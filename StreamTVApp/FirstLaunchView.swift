//
//  FirstLaunchView.swift
//  StreamTV
//
//  First launch requirements dialog
//

import SwiftUI
import AppKit

struct FirstLaunchView: View {
    @Binding var isPresented: Bool
    @State private var pythonInstalled = false
    @State private var homebrewInstalled = false
    @State private var ffmpegInstalled = false
    
    var body: some View {
        VStack(spacing: 20) {
            Text("StreamTV Setup")
                .font(.largeTitle)
                .fontWeight(.bold)
            
            Text("StreamTV requires the following dependencies:")
                .font(.headline)
            
            VStack(alignment: .leading, spacing: 12) {
                DependencyRow(
                    name: "Python 3.8+",
                    installed: pythonInstalled,
                    required: true,
                    description: nil
                )
                
                DependencyRow(
                    name: "Homebrew",
                    installed: homebrewInstalled,
                    required: true,
                    description: "Required to install FFmpeg"
                )
                
                DependencyRow(
                    name: "FFmpeg",
                    installed: ffmpegInstalled,
                    required: true,
                    description: "Required for video transcoding"
                )
            }
            .padding()
            .background(Color(NSColor.controlBackgroundColor))
            .cornerRadius(8)
            
            if !allDependenciesMet {
                Text("Please install the required dependencies before continuing.")
                    .foregroundColor(.red)
                    .font(.caption)
            }
            
            HStack {
                Button("Cancel") {
                    NSApplication.shared.terminate(nil)
                }
                
                Button("Continue") {
                    isPresented = false
                }
                .disabled(!allDependenciesMet)
                .keyboardShortcut(.defaultAction)
            }
        }
        .padding(30)
        .frame(width: 500, height: 400)
        .onAppear {
            checkDependencies()
        }
    }
    
    private var allDependenciesMet: Bool {
        return pythonInstalled && homebrewInstalled && ffmpegInstalled
    }
    
    private func checkDependencies() {
        // Check Python
        let (installed, _) = PythonManager.shared.checkPythonVersion()
        pythonInstalled = installed
        
        // Check Homebrew
        let (installedHB, _) = FFmpegManager.shared.homebrewInstalled()
        homebrewInstalled = installedHB
        
        // Check FFmpeg
        let (installedFF, _, _) = FFmpegManager.shared.ffmpegInstalled()
        ffmpegInstalled = installedFF
    }
}

struct DependencyRow: View {
    let name: String
    let installed: Bool
    let required: Bool
    let description: String?
    
    var body: some View {
        HStack {
            Image(systemName: installed ? "checkmark.circle.fill" : "xmark.circle.fill")
                .foregroundColor(installed ? .green : .red)
            
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(name)
                        .fontWeight(.semibold)
                    if required {
                        Text("(Required)")
                            .font(.caption)
                            .foregroundColor(.red)
                    }
                }
                
                if let description = description {
                    Text(description)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            
            Spacer()
        }
    }
}

