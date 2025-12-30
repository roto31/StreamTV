//
//  StreamTVApp.swift
//  StreamTV
//
//  Main application entry point
//

import SwiftUI
import AppKit
import UserNotifications

@main
struct StreamTVApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    
    var body: some Scene {
        Settings {
            EmptyView()
        }
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    private var menuBarView: MenuBarView?
    private var firstLaunchWindow: NSWindow?
    private let firstLaunchKey = "HasCompletedFirstLaunch"
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Request notification permissions
        requestNotificationPermissions()
        
        // Check if first launch
        if !UserDefaults.standard.bool(forKey: firstLaunchKey) {
            showFirstLaunchDialog()
        } else {
            initializeApp()
        }
        
        // Start periodic dependency checks
        DependencyUpdater.shared.performPeriodicCheckIfNeeded()
    }
    
    func applicationWillTerminate(_ notification: Notification) {
        // Stop server gracefully
        ServerManager.shared.stopServer()
    }
    
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return false // Keep app running even if windows close
    }
    
    // MARK: - First Launch
    
    private func showFirstLaunchDialog() {
        let hostingView = NSHostingView(rootView: FirstLaunchView(isPresented: .constant(true)))
        hostingView.frame = NSRect(x: 0, y: 0, width: 500, height: 400)
        
        let window = NSWindow(
            contentRect: hostingView.frame,
            styleMask: [.titled, .closable],
            backing: .buffered,
            defer: false
        )
        window.contentView = hostingView
        window.title = "StreamTV Setup"
        window.center()
        window.isReleasedWhenClosed = false
        window.makeKeyAndOrderFront(nil)
        
        firstLaunchWindow = window
        
        // Monitor for window close
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(firstLaunchWindowClosed),
            name: NSWindow.willCloseNotification,
            object: window
        )
    }
    
    @objc private func firstLaunchWindowClosed() {
        // Mark first launch as complete
        UserDefaults.standard.set(true, forKey: firstLaunchKey)
        firstLaunchWindow = nil
        initializeApp()
    }
    
    // MARK: - App Initialization
    
    private func initializeApp() {
        // Initialize menu bar
        menuBarView = MenuBarView()
        
        // Setup Python environment if needed
        setupPythonEnvironment()
        
        // Check FFmpeg
        checkFFmpeg()
        
        // Check Ollama (non-blocking)
        checkOllama()
    }
    
    private func setupPythonEnvironment() {
        let pythonManager = PythonManager.shared
        
        // Check Python
        let (installed, _) = pythonManager.checkPythonVersion()
        guard installed else {
            showError("Python 3.8+ is required. Please install Python from python.org or via Homebrew.")
            return
        }
        
        // Create venv if needed
        if !pythonManager.venvExists() {
            do {
                try pythonManager.createVenv()
                try pythonManager.installDependencies()
            } catch {
                showError("Failed to setup Python environment: \(error.localizedDescription)")
            }
        }
    }
    
    private func checkFFmpeg() {
        let ffmpegManager = FFmpegManager.shared
        let (installed, _, _) = ffmpegManager.ffmpegInstalled()
        
        if !installed {
            let (homebrewInstalled, brewPath) = ffmpegManager.homebrewInstalled()
            
            if homebrewInstalled, let brewPath = brewPath {
                let alert = NSAlert()
                alert.messageText = "FFmpeg Required"
                alert.informativeText = "FFmpeg is required for video transcoding. Would you like to install it via Homebrew?"
                alert.addButton(withTitle: "Install")
                alert.addButton(withTitle: "Cancel")
                alert.alertStyle = .informational
                
                if alert.runModal() == .alertFirstButtonReturn {
                    do {
                        let _ = try ffmpegManager.installFFmpeg(brewPath: brewPath)
                        // FFmpeg installed successfully
                    } catch {
                        showError("Failed to install FFmpeg: \(error.localizedDescription)")
                    }
                }
            } else {
                showError("FFmpeg is required but not installed. Please install Homebrew from https://brew.sh and then install FFmpeg.")
            }
        }
    }
    
    private func checkOllama() {
        let ollamaChecker = OllamaChecker.shared
        let (installed, _) = ollamaChecker.ollamaInstalled()
        
        if !installed && ollamaChecker.shouldShowPrompt() {
            let alert = NSAlert()
            alert.messageText = "Ollama (Optional)"
            alert.informativeText = "Ollama is an optional AI integration. Would you like to install it?"
            alert.addButton(withTitle: "Learn More")
            alert.addButton(withTitle: "Don't Show Again")
            alert.addButton(withTitle: "Cancel")
            alert.alertStyle = .informational
            
            let response = alert.runModal()
            
            if response == .alertFirstButtonReturn {
                if let url = URL(string: "https://ollama.ai") {
                    NSWorkspace.shared.open(url)
                }
            } else if response == .alertSecondButtonReturn {
                ollamaChecker.setSkipPrompt(true)
            }
        }
    }
    
    // MARK: - Helpers
    
    private func requestNotificationPermissions() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { granted, error in
            if let error = error {
                print("Notification permission error: \(error)")
            }
        }
    }
    
    private func showError(_ message: String) {
        let alert = NSAlert()
        alert.messageText = "Error"
        alert.informativeText = message
        alert.alertStyle = .warning
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }
}

