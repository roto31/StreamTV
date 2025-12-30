//
//  OllamaChecker.swift
//  StreamTV
//
//  Checks for Ollama installation (optional)
//

import Foundation

class OllamaChecker {
    static let shared = OllamaChecker()
    
    private let ollamaURL = URL(string: "http://localhost:11434")!
    private let skipPromptKey = "OllamaSkipPrompt"
    
    private init() {}
    
    // MARK: - Ollama Check
    
    func ollamaInstalled() -> (installed: Bool, version: String?) {
        // Check for ollama command
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/which")
        process.arguments = ["ollama"]
        
        let pipe = Pipe()
        process.standardOutput = pipe
        
        do {
            try process.run()
            process.waitUntilExit()
            
            if process.terminationStatus == 0 {
                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                let ollamaPath = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
                
                if !ollamaPath.isEmpty {
                    // Get version
                    let versionProcess = Process()
                    versionProcess.executableURL = URL(fileURLWithPath: ollamaPath)
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
            }
        } catch {
            print("Error checking Ollama: \(error)")
        }
        
        return (false, nil)
    }
    
    // MARK: - Ollama Running Check
    
    func ollamaRunning() -> Bool {
        var running = false
        let semaphore = DispatchSemaphore(value: 0)
        
        let task = URLSession.shared.dataTask(with: ollamaURL) { data, response, error in
            if let httpResponse = response as? HTTPURLResponse {
                running = httpResponse.statusCode == 200 || httpResponse.statusCode == 404
            }
            semaphore.signal()
        }
        
        task.resume()
        _ = semaphore.wait(timeout: .now() + 2.0) // 2 second timeout
        
        return running
    }
    
    // MARK: - Skip Prompt Preference
    
    func shouldShowPrompt() -> Bool {
        return !UserDefaults.standard.bool(forKey: skipPromptKey)
    }
    
    func setSkipPrompt(_ skip: Bool) {
        UserDefaults.standard.set(skip, forKey: skipPromptKey)
    }
    
    // MARK: - Latest Version Check
    
    func getLatestVersion() -> String? {
        // Ollama doesn't have a simple version check via command line
        // This would require checking their GitHub releases or API
        // For now, return nil and handle in DependencyUpdater
        return nil
    }
}

