//
//  ServerManager.swift
//  StreamTV
//
//  Manages StreamTV server process lifecycle
//

import Foundation
import Combine
import AppKit

enum ServerStatus: Equatable {
    case stopped
    case starting
    case running
    case stopping
    case error(String)
    
    static func == (lhs: ServerStatus, rhs: ServerStatus) -> Bool {
        switch (lhs, rhs) {
        case (.stopped, .stopped),
             (.starting, .starting),
             (.running, .running),
             (.stopping, .stopping):
            return true
        case (.error(let lhsMessage), .error(let rhsMessage)):
            return lhsMessage == rhsMessage
        default:
            return false
        }
    }
}

class ServerManager: ObservableObject {
    static let shared = ServerManager()
    
    @Published var status: ServerStatus = .stopped
    @Published var healthCheckFailed = false
    
    private var process: Process?
    private var healthCheckTimer: Timer?
    private let healthCheckURL = URL(string: "http://localhost:8410/api/health")!
    private let logFileURL: URL
    
    private init() {
        let fileManager = FileManager.default
        let appSupport = fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let streamtvSupport = appSupport.appendingPathComponent("StreamTV")
        let logsDir = streamtvSupport.appendingPathComponent("logs")
        
        try? fileManager.createDirectory(at: logsDir, withIntermediateDirectories: true)
        logFileURL = logsDir.appendingPathComponent("streamtv.log")
    }
    
    // MARK: - Server Control
    
    func startServer() throws {
        guard case .stopped = status else {
            throw ServerManagerError.serverAlreadyRunning
        }
        
        status = .starting
        
        // Get Python path
        guard let pythonPath = PythonManager.shared.pythonPath() else {
            status = .error("Python virtual environment not found")
            throw ServerManagerError.pythonNotFound
        }
        
        // Get streamtv module path
        guard let streamtvPath = PythonManager.shared.streamtvModulePath() else {
            status = .error("StreamTV module not found in bundle")
            throw ServerManagerError.streamtvNotFound
        }
        
        // Create process
        let newProcess = Process()
        newProcess.executableURL = URL(fileURLWithPath: pythonPath)
        newProcess.arguments = ["-m", "streamtv.main"]
        
        // Set environment
        var environment = ProcessInfo.processInfo.environment
        environment["PYTHONPATH"] = streamtvPath
        newProcess.environment = environment
        
        // Redirect output to log file
        let logFileHandle = try FileHandle(forWritingTo: logFileURL)
        logFileHandle.seekToEndOfFile()
        newProcess.standardOutput = logFileHandle
        newProcess.standardError = logFileHandle
        
        // Handle termination
        newProcess.terminationHandler = { [weak self] process in
            DispatchQueue.main.async {
                if process.terminationStatus != 0 {
                    self?.status = .error("Server exited with code \(process.terminationStatus)")
                } else {
                    self?.status = .stopped
                }
                self?.stopHealthCheck()
            }
        }
        
        // Start process
        try newProcess.run()
        process = newProcess
        
        // Start health check
        startHealthCheck()
    }
    
    func stopServer() {
        guard let process = process else {
            status = .stopped
            return
        }
        
        status = .stopping
        stopHealthCheck()
        
        // Send SIGTERM
        process.terminate()
        
        // Wait up to 5 seconds for graceful shutdown
        let group = DispatchGroup()
        group.enter()
        
        DispatchQueue.global().async {
            process.waitUntilExit()
            group.leave()
        }
        
        let result = group.wait(timeout: .now() + 5.0)
        
        if result == .timedOut {
            // Force kill
            process.terminate()
            process.waitUntilExit()
        }
        
        self.process = nil
        status = .stopped
    }
    
    // MARK: - Health Check
    
    private func startHealthCheck() {
        healthCheckTimer = Timer.scheduledTimer(withTimeInterval: 2.0, repeats: true) { [weak self] _ in
            self?.checkHealth()
        }
    }
    
    private func stopHealthCheck() {
        healthCheckTimer?.invalidate()
        healthCheckTimer = nil
    }
    
    private func checkHealth() {
        let task = URLSession.shared.dataTask(with: healthCheckURL) { [weak self] data, response, error in
            DispatchQueue.main.async {
                if let httpResponse = response as? HTTPURLResponse,
                   httpResponse.statusCode == 200 {
                    if case .starting = self?.status {
                        self?.status = .running
                    }
                    self?.healthCheckFailed = false
                } else {
                    self?.healthCheckFailed = true
                    if case .running = self?.status {
                        self?.status = .error("Health check failed")
                    }
                }
            }
        }
        task.resume()
    }
    
    // MARK: - Log Access
    
    func getLogFileURL() -> URL {
        return logFileURL
    }
    
    func openLogFile() {
        NSWorkspace.shared.open(logFileURL)
    }
}

enum ServerManagerError: LocalizedError {
    case serverAlreadyRunning
    case pythonNotFound
    case streamtvNotFound
    case startFailed(String)
    
    var errorDescription: String? {
        switch self {
        case .serverAlreadyRunning:
            return "Server is already running"
        case .pythonNotFound:
            return "Python virtual environment not found"
        case .streamtvNotFound:
            return "StreamTV module not found in app bundle"
        case .startFailed(let message):
            return "Failed to start server: \(message)"
        }
    }
}

