//
//  MenuBarView.swift
//  StreamTV
//
//  Menu bar UI with NSStatusItem
//

import AppKit
import SwiftUI

class MenuBarView: NSObject {
    private var statusItem: NSStatusItem?
    private var menu: NSMenu?
    private let serverManager = ServerManager.shared
    private let dependencyUpdater = DependencyUpdater.shared
    
    override init() {
        super.init()
        setupMenuBar()
        observeServerStatus()
    }
    
    // MARK: - Setup
    
    private func setupMenuBar() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        
        guard let button = statusItem?.button else { return }
        
        // Set initial icon (gray dot for stopped)
        button.image = NSImage(systemSymbolName: "circle.fill", accessibilityDescription: "StreamTV")
        button.image?.isTemplate = true
        
        // Create menu
        menu = NSMenu()
        menu?.delegate = self
        
        updateMenu()
    }
    
    private func observeServerStatus() {
        // Observe server status changes
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(serverStatusChanged),
            name: NSNotification.Name("ServerStatusChanged"),
            object: nil
        )
    }
    
    @objc private func serverStatusChanged() {
        updateMenu()
        updateStatusIcon()
    }
    
    // MARK: - Menu Updates
    
    private func updateMenu() {
        guard let menu = menu else { return }
        
        menu.removeAllItems()
        
        // Header
        let headerItem = NSMenuItem(title: "StreamTV", action: nil, keyEquivalent: "")
        headerItem.isEnabled = false
        menu.addItem(headerItem)
        menu.addItem(NSMenuItem.separator())
        
        // Open Web Interface
        let webInterfaceItem = NSMenuItem(
            title: "Open Web Interface",
            action: #selector(openWebInterface),
            keyEquivalent: ""
        )
        webInterfaceItem.target = self
        menu.addItem(webInterfaceItem)
        
        // View Logs
        let logsItem = NSMenuItem(
            title: "View Logs",
            action: #selector(viewLogs),
            keyEquivalent: ""
        )
        logsItem.target = self
        menu.addItem(logsItem)
        
        menu.addItem(NSMenuItem.separator())
        
        // Check for Updates
        let updatesItem = NSMenuItem(
            title: dependencyUpdater.isChecking ? "Checking for Updates..." : "Check for Updates",
            action: #selector(checkForUpdates),
            keyEquivalent: ""
        )
        updatesItem.target = self
        updatesItem.isEnabled = !dependencyUpdater.isChecking
        menu.addItem(updatesItem)
        
        menu.addItem(NSMenuItem.separator())
        
        // Start/Stop Server
        let serverItem: NSMenuItem
        switch serverManager.status {
        case .stopped:
            serverItem = NSMenuItem(
                title: "Start Server",
                action: #selector(startServer),
                keyEquivalent: ""
            )
        case .running:
            serverItem = NSMenuItem(
                title: "Stop Server",
                action: #selector(stopServer),
                keyEquivalent: ""
            )
        case .starting, .stopping:
            serverItem = NSMenuItem(
                title: serverManager.status == .starting ? "Starting..." : "Stopping...",
                action: nil,
                keyEquivalent: ""
            )
            serverItem.isEnabled = false
        case .error:
            serverItem = NSMenuItem(
                title: "Restart Server",
                action: #selector(startServer),
                keyEquivalent: ""
            )
        }
        serverItem.target = self
        menu.addItem(serverItem)
        
        menu.addItem(NSMenuItem.separator())
        
        // About
        let aboutItem = NSMenuItem(
            title: "About StreamTV",
            action: #selector(showAbout),
            keyEquivalent: ""
        )
        aboutItem.target = self
        menu.addItem(aboutItem)
        
        // Quit
        let quitItem = NSMenuItem(
            title: "Quit StreamTV",
            action: #selector(quit),
            keyEquivalent: "q"
        )
        quitItem.target = self
        menu.addItem(quitItem)
        
        statusItem?.menu = menu
    }
    
    private func updateStatusIcon() {
        guard let button = statusItem?.button else { return }
        
        let iconName: String
        switch serverManager.status {
        case .stopped:
            iconName = "circle.fill"
        case .starting, .stopping:
            iconName = "circle.fill"
        case .running:
            iconName = "circle.fill"
        case .error:
            iconName = "circle.fill"
        }
        
        button.image = NSImage(systemSymbolName: iconName, accessibilityDescription: "StreamTV")
        button.image?.isTemplate = true
        
        // Set color based on status
        if #available(macOS 11.0, *) {
            switch serverManager.status {
            case .running:
                button.contentTintColor = .systemGreen
            case .starting, .stopping:
                button.contentTintColor = .systemYellow
            case .error:
                button.contentTintColor = .systemRed
            case .stopped:
                button.contentTintColor = .systemGray
            }
        }
    }
    
    // MARK: - Menu Actions
    
    @objc private func openWebInterface() {
        if let url = URL(string: "http://localhost:8410") {
            NSWorkspace.shared.open(url)
        }
    }
    
    @objc private func viewLogs() {
        serverManager.openLogFile()
    }
    
    @objc private func checkForUpdates() {
        Task {
            let results = await dependencyUpdater.checkForUpdates()
            await MainActor.run {
                dependencyUpdater.showUpdateResultsDialog(results: results)
                updateMenu()
            }
        }
    }
    
    @objc private func startServer() {
        do {
            try serverManager.startServer()
            updateMenu()
        } catch {
            let alert = NSAlert(error: error)
            alert.runModal()
        }
    }
    
    @objc private func stopServer() {
        serverManager.stopServer()
        updateMenu()
    }
    
    @objc private func showAbout() {
        let alert = NSAlert()
        alert.messageText = "StreamTV"
        alert.informativeText = "A menu bar application for managing StreamTV server"
        alert.alertStyle = .informational
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }
    
    @objc private func quit() {
        serverManager.stopServer()
        NSApplication.shared.terminate(nil)
    }
}

extension MenuBarView: NSMenuDelegate {
    func menuWillOpen(_ menu: NSMenu) {
        updateMenu()
    }
}

