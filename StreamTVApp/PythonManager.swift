//
//  PythonManager.swift
//  StreamTV
//
//  Manages Python virtual environment and dependencies
//

import Foundation

class PythonManager {
    static let shared = PythonManager()
    
    private let appSupportURL: URL
    private let venvURL: URL
    private let requirementsPath: String?
    
    private init() {
        let fileManager = FileManager.default
        let appSupport = fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        appSupportURL = appSupport.appendingPathComponent("StreamTV")
        venvURL = appSupportURL.appendingPathComponent("venv")
        
        // Get requirements.txt from bundle
        if let requirementsURL = Bundle.main.path(forResource: "requirements", ofType: "txt") {
            requirementsPath = requirementsURL
        } else {
            requirementsPath = nil
        }
        
        // Create Application Support directory if needed
        try? fileManager.createDirectory(at: appSupportURL, withIntermediateDirectories: true)
    }
    
    // MARK: - Python Version Check
    
    func checkPythonVersion() -> (installed: Bool, version: String?) {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/which")
        process.arguments = ["python3"]
        
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        
        do {
            try process.run()
            process.waitUntilExit()
            
            if process.terminationStatus == 0 {
                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                let pythonPath = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
                
                // Get version
                let versionProcess = Process()
                versionProcess.executableURL = URL(fileURLWithPath: pythonPath)
                versionProcess.arguments = ["--version"]
                
                let versionPipe = Pipe()
                versionProcess.standardOutput = versionPipe
                versionProcess.standardError = versionPipe
                
                try versionProcess.run()
                versionProcess.waitUntilExit()
                
                if versionProcess.terminationStatus == 0 {
                    let versionData = versionPipe.fileHandleForReading.readDataToEndOfFile()
                    let version = String(data: versionData, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? "Unknown"
                    return (true, version)
                }
            }
        } catch {
            print("Error checking Python: \(error)")
        }
        
        return (false, nil)
    }
    
    // MARK: - Virtual Environment Management
    
    func venvExists() -> Bool {
        let pythonPath = venvURL.appendingPathComponent("bin/python3")
        return FileManager.default.fileExists(atPath: pythonPath.path)
    }
    
    func createVenv() throws {
        let (installed, _) = checkPythonVersion()
        guard installed else {
            throw PythonManagerError.pythonNotInstalled
        }
        
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        process.arguments = ["-m", "venv", venvURL.path]
        process.currentDirectoryURL = appSupportURL
        
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        
        try process.run()
        process.waitUntilExit()
        
        guard process.terminationStatus == 0 else {
            let errorData = pipe.fileHandleForReading.readDataToEndOfFile()
            let errorMessage = String(data: errorData, encoding: .utf8) ?? "Unknown error"
            throw PythonManagerError.venvCreationFailed(errorMessage)
        }
    }
    
    // MARK: - Dependency Installation
    
    func installDependencies() throws {
        guard venvExists() else {
            throw PythonManagerError.venvNotFound
        }
        
        guard let requirementsPath = requirementsPath else {
            throw PythonManagerError.requirementsNotFound
        }
        
        let pipPath = venvURL.appendingPathComponent("bin/pip3")
        guard FileManager.default.fileExists(atPath: pipPath.path) else {
            throw PythonManagerError.pipNotFound
        }
        
        let process = Process()
        process.executableURL = pipPath
        process.arguments = ["install", "-r", requirementsPath]
        process.currentDirectoryURL = appSupportURL
        
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        
        try process.run()
        process.waitUntilExit()
        
        guard process.terminationStatus == 0 else {
            let errorData = pipe.fileHandleForReading.readDataToEndOfFile()
            let errorMessage = String(data: errorData, encoding: .utf8) ?? "Unknown error"
            throw PythonManagerError.dependencyInstallationFailed(errorMessage)
        }
    }
    
    // MARK: - Python Path
    
    func pythonPath() -> String? {
        let pythonPath = venvURL.appendingPathComponent("bin/python3")
        guard FileManager.default.fileExists(atPath: pythonPath.path) else {
            return nil
        }
        return pythonPath.path
    }
    
    func streamtvModulePath() -> String? {
        guard let resourcePath = Bundle.main.resourcePath else {
            return nil
        }
        let streamtvPath = (resourcePath as NSString).appendingPathComponent("streamtv")
        guard FileManager.default.fileExists(atPath: streamtvPath) else {
            return nil
        }
        return streamtvPath
    }
}

enum PythonManagerError: LocalizedError {
    case pythonNotInstalled
    case venvNotFound
    case venvCreationFailed(String)
    case requirementsNotFound
    case pipNotFound
    case dependencyInstallationFailed(String)
    
    var errorDescription: String? {
        switch self {
        case .pythonNotInstalled:
            return "Python 3.8+ is not installed. Please install Python from python.org or via Homebrew."
        case .venvNotFound:
            return "Virtual environment not found. Please create it first."
        case .venvCreationFailed(let message):
            return "Failed to create virtual environment: \(message)"
        case .requirementsNotFound:
            return "requirements.txt not found in app bundle."
        case .pipNotFound:
            return "pip not found in virtual environment."
        case .dependencyInstallationFailed(let message):
            return "Failed to install dependencies: \(message)"
        }
    }
}

