//
//  DependencyUpdater.swift
//  StreamTV
//
//  Manages periodic dependency version checking and update alerts
//

import Foundation
import Combine
import AppKit
import UserNotifications

enum DependencyStatus {
    case upToDate
    case updateAvailable(String)
    case notInstalled
    case error(String)
}

struct DependencyCheckResult {
    let name: String
    let status: DependencyStatus
    let currentVersion: String?
    let latestVersion: String?
    let updateInstructions: String?
}

class DependencyUpdater: ObservableObject {
    static let shared = DependencyUpdater()
    
    @Published var isChecking = false
    @Published var lastCheckDate: Date?
    
    private let lastCheckKey = "LastDependencyCheck"
    private let checkInterval: TimeInterval = 24 * 60 * 60 // 24 hours
    
    private init() {
        if let lastCheck = UserDefaults.standard.object(forKey: lastCheckKey) as? Date {
            lastCheckDate = lastCheck
        }
    }
    
    // MARK: - Manual Update Check
    
    func checkForUpdates() async -> [DependencyCheckResult] {
        await MainActor.run {
            isChecking = true
        }
        
        defer {
            Task { @MainActor in
                isChecking = false
                lastCheckDate = Date()
                UserDefaults.standard.set(lastCheckDate, forKey: lastCheckKey)
            }
        }
        
        var results: [DependencyCheckResult] = []
        
        // Check Python
        let pythonResult = await checkPython()
        results.append(pythonResult)
        
        // Check FFmpeg
        let ffmpegResult = await checkFFmpeg()
        results.append(ffmpegResult)
        
        // Check Ollama
        let ollamaResult = await checkOllama()
        results.append(ollamaResult)
        
        return results
    }
    
    // MARK: - Individual Dependency Checks
    
    private func checkPython() async -> DependencyCheckResult {
        let (installed, currentVersion) = PythonManager.shared.checkPythonVersion()
        
        guard installed, let version = currentVersion else {
            return DependencyCheckResult(
                name: "Python",
                status: .notInstalled,
                currentVersion: nil,
                latestVersion: nil,
                updateInstructions: "Install Python 3.8+ from python.org or via Homebrew: brew install python@3.11"
            )
        }
        
        // Parse version (e.g., "Python 3.11.5")
        let versionComponents = version.components(separatedBy: " ")
        let versionString = versionComponents.last ?? version
        
        // For now, assume up to date (would need to fetch from python.org API)
        return DependencyCheckResult(
            name: "Python",
            status: .upToDate,
            currentVersion: versionString,
            latestVersion: nil,
            updateInstructions: nil
        )
    }
    
    private func checkFFmpeg() async -> DependencyCheckResult {
        let (installed, currentVersion, _) = FFmpegManager.shared.ffmpegInstalled()
        
        guard installed, let version = currentVersion else {
            return DependencyCheckResult(
                name: "FFmpeg",
                status: .notInstalled,
                currentVersion: nil,
                latestVersion: nil,
                updateInstructions: "Install FFmpeg via Homebrew: brew install ffmpeg"
            )
        }
        
        // Get latest version from Homebrew
        let latestVersion = FFmpegManager.shared.getLatestVersion()
        
        if let latest = latestVersion, latest != version {
            return DependencyCheckResult(
                name: "FFmpeg",
                status: .updateAvailable(latest),
                currentVersion: version,
                latestVersion: latest,
                updateInstructions: "Update FFmpeg: brew upgrade ffmpeg"
            )
        }
        
        return DependencyCheckResult(
            name: "FFmpeg",
            status: .upToDate,
            currentVersion: version,
            latestVersion: latestVersion,
            updateInstructions: nil
        )
    }
    
    private func checkOllama() async -> DependencyCheckResult {
        let (installed, currentVersion) = OllamaChecker.shared.ollamaInstalled()
        
        guard installed, let version = currentVersion else {
            return DependencyCheckResult(
                name: "Ollama",
                status: .notInstalled,
                currentVersion: nil,
                latestVersion: nil,
                updateInstructions: "Ollama is optional. Install from https://ollama.ai"
            )
        }
        
        // Ollama version checking would require API call
        return DependencyCheckResult(
            name: "Ollama",
            status: .upToDate,
            currentVersion: version,
            latestVersion: nil,
            updateInstructions: nil
        )
    }
    
    // MARK: - Periodic Check
    
    func shouldPerformPeriodicCheck() -> Bool {
        guard let lastCheck = lastCheckDate else {
            return true
        }
        return Date().timeIntervalSince(lastCheck) >= checkInterval
    }
    
    func performPeriodicCheckIfNeeded() {
        guard shouldPerformPeriodicCheck() else {
            return
        }
        
        Task {
            let results = await checkForUpdates()
            let updatesAvailable = results.contains { result in
                if case .updateAvailable = result.status {
                    return true
                }
                return false
            }
            
            if updatesAvailable {
                await showUpdateNotification(results: results)
            }
        }
    }
    
    // MARK: - Notifications
    
    private func showUpdateNotification(results: [DependencyCheckResult]) async {
        let updateResults = results.filter { result in
            if case .updateAvailable = result.status {
                return true
            }
            return false
        }
        
        guard !updateResults.isEmpty else { return }
        
        let content = UNMutableNotificationContent()
        content.title = "StreamTV: Updates Available"
        content.body = "\(updateResults.count) dependency update(s) available"
        content.sound = .default
        
        let request = UNNotificationRequest(
            identifier: "dependency-updates",
            content: content,
            trigger: nil
        )
        
        do {
            try await UNUserNotificationCenter.current().add(request)
        } catch {
            print("Failed to show notification: \(error)")
        }
    }
    
    func showUpdateResultsDialog(results: [DependencyCheckResult]) {
        let alert = NSAlert()
        alert.messageText = "Dependency Update Check"
        alert.informativeText = formatResults(results: results)
        alert.alertStyle = NSAlert.Style.informational
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }
    
    private func formatResults(results: [DependencyCheckResult]) -> String {
        var lines: [String] = []
        
        for result in results {
            switch result.status {
            case .upToDate:
                lines.append("\(result.name): Up to date (\(result.currentVersion ?? "Unknown"))")
            case .updateAvailable(let latest):
                lines.append("\(result.name): Update available (\(result.currentVersion ?? "Unknown") → \(latest))")
                if let instructions = result.updateInstructions {
                    lines.append("  \(instructions)")
                }
            case .notInstalled:
                lines.append("\(result.name): Not installed")
                if let instructions = result.updateInstructions {
                    lines.append("  \(instructions)")
                }
            case .error(let message):
                lines.append("\(result.name): Error - \(message)")
            }
        }
        
        return lines.joined(separator: "\n")
    }
}

