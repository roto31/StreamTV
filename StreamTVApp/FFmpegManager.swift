//
//  FFmpegManager.swift
//  StreamTV
//
//  Manages FFmpeg installation via Homebrew
//

import Foundation

class FFmpegManager {
    static let shared = FFmpegManager()
    
    private let homebrewPaths = [
        "/opt/homebrew/bin/brew",  // Apple Silicon
        "/usr/local/bin/brew"       // Intel
    ]
    
    private init() {}
    
    // MARK: - Homebrew Check
    
    func homebrewInstalled() -> (installed: Bool, path: String?) {
        for path in homebrewPaths {
            if FileManager.default.fileExists(atPath: path) {
                return (true, path)
            }
        }
        
        // Check PATH
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/which")
        process.arguments = ["brew"]
        
        let pipe = Pipe()
        process.standardOutput = pipe
        
        do {
            try process.run()
            process.waitUntilExit()
            
            if process.terminationStatus == 0 {
                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                let brewPath = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
                if !brewPath.isEmpty {
                    return (true, brewPath)
                }
            }
        } catch {
            print("Error checking Homebrew: \(error)")
        }
        
        return (false, nil)
    }
    
    // MARK: - FFmpeg Check
    
    func ffmpegInstalled() -> (installed: Bool, version: String?, path: String?) {
        // Check common locations
        let ffmpegPaths = [
            "/opt/homebrew/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/usr/bin/ffmpeg"
        ]
        
        for path in ffmpegPaths {
            if FileManager.default.fileExists(atPath: path) {
                if let version = getFFmpegVersion(path: path) {
                    return (true, version, path)
                }
            }
        }
        
        // Check PATH
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/which")
        process.arguments = ["ffmpeg"]
        
        let pipe = Pipe()
        process.standardOutput = pipe
        
        do {
            try process.run()
            process.waitUntilExit()
            
            if process.terminationStatus == 0 {
                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                let ffmpegPath = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
                if !ffmpegPath.isEmpty, let version = getFFmpegVersion(path: ffmpegPath) {
                    return (true, version, ffmpegPath)
                }
            }
        } catch {
            print("Error checking FFmpeg: \(error)")
        }
        
        return (false, nil, nil)
    }
    
    private func getFFmpegVersion(path: String) -> String? {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: path)
        process.arguments = ["-version"]
        
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        
        do {
            try process.run()
            process.waitUntilExit()
            
            if process.terminationStatus == 0 {
                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                let output = String(data: data, encoding: .utf8) ?? ""
                // Extract version from first line (e.g., "ffmpeg version 6.1.1")
                if let firstLine = output.components(separatedBy: .newlines).first,
                   let versionRange = firstLine.range(of: "version ") {
                    let version = String(firstLine[versionRange.upperBound...]).trimmingCharacters(in: .whitespaces)
                    return version.components(separatedBy: " ").first ?? version
                }
            }
        } catch {
            print("Error getting FFmpeg version: \(error)")
        }
        
        return nil
    }
    
    // MARK: - FFmpeg Installation
    
    func installFFmpeg(brewPath: String) throws -> String {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: brewPath)
        process.arguments = ["install", "ffmpeg"]
        
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        
        try process.run()
        process.waitUntilExit()
        
        guard process.terminationStatus == 0 else {
            let errorData = pipe.fileHandleForReading.readDataToEndOfFile()
            let errorMessage = String(data: errorData, encoding: .utf8) ?? "Unknown error"
            throw FFmpegManagerError.installationFailed(errorMessage)
        }
        
        // Verify installation
        let (installed, _, path) = ffmpegInstalled()
        guard installed, let ffmpegPath = path else {
            throw FFmpegManagerError.verificationFailed
        }
        
        // Store path in UserDefaults
        UserDefaults.standard.set(ffmpegPath, forKey: "FFmpegPath")
        
        return ffmpegPath
    }
    
    // MARK: - Latest Version Check
    
    func getLatestVersion() -> String? {
        let (installed, brewPath) = homebrewInstalled()
        guard installed, let brewPath = brewPath else {
            return nil
        }
        
        let process = Process()
        process.executableURL = URL(fileURLWithPath: brewPath)
        process.arguments = ["info", "ffmpeg"]
        
        let pipe = Pipe()
        process.standardOutput = pipe
        
        do {
            try process.run()
            process.waitUntilExit()
            
            if process.terminationStatus == 0 {
                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                let output = String(data: data, encoding: .utf8) ?? ""
                
                // Parse version from output (look for version line)
                for line in output.components(separatedBy: .newlines) {
                    if line.contains("ffmpeg:") {
                        // Extract version from line like "ffmpeg: stable 6.1.1"
                        let components = line.components(separatedBy: " ")
                        if components.count >= 3, components[1] == "stable" {
                            return components[2]
                        }
                    }
                }
            }
        } catch {
            print("Error getting latest FFmpeg version: \(error)")
        }
        
        return nil
    }
    
    // MARK: - Stored Path
    
    func storedFFmpegPath() -> String? {
        return UserDefaults.standard.string(forKey: "FFmpegPath")
    }
}

enum FFmpegManagerError: LocalizedError {
    case homebrewNotInstalled
    case installationFailed(String)
    case verificationFailed
    
    var errorDescription: String? {
        switch self {
        case .homebrewNotInstalled:
            return "Homebrew is not installed. Please install Homebrew from https://brew.sh"
        case .installationFailed(let message):
            return "Failed to install FFmpeg: \(message)"
        case .verificationFailed:
            return "FFmpeg installation completed but verification failed."
        }
    }
}

