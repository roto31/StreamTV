import SwiftUI
import AVKit

// Simple EPG grid example (SwiftUI-only). For large guides, consider a Compositional Layout via UIViewControllerRepresentable.
public struct EPGView: View {
    public let channels: [Channel]
    public let programmesByChannel: [String: [Programme]]
    public let timelineStart: Date
    public let hourWidth: CGFloat

    public init(channels: [Channel], programmesByChannel: [String: [Programme]], timelineStart: Date, hourWidth: CGFloat = 240) {
        self.channels = channels
        self.programmesByChannel = programmesByChannel
        self.timelineStart = timelineStart
        self.hourWidth = hourWidth
    }

    public var body: some View {
        ScrollView([.vertical, .horizontal]) {
            VStack(alignment: .leading, spacing: 12) {
                ForEach(channels) { channel in
                    VStack(alignment: .leading, spacing: 4) {
                        Text("\(channel.id) • \(channel.name)")
                            .font(.headline)
                        HStack(alignment: .top, spacing: 4) {
                            if let progs = programmesByChannel[channel.id] {
                                ForEach(progs) { p in
                                    ProgrammeBlock(programme: p, timelineStart: timelineStart, hourWidth: hourWidth)
                                }
                            }
                        }
                    }
                }
            }
            .padding()
        }
    }
}

struct ProgrammeBlock: View {
    let programme: Programme
    let timelineStart: Date
    let hourWidth: CGFloat

    var durationHours: CGFloat {
        CGFloat(programme.end.timeIntervalSince(programme.start) / 3600.0)
    }
    var offsetHours: CGFloat {
        CGFloat(programme.start.timeIntervalSince(timelineStart) / 3600.0)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(programme.title).font(.subheadline).bold().lineLimit(2)
            if let sub = programme.subtitle { Text(sub).font(.caption).lineLimit(1) }
            if let desc = programme.desc { Text(desc).font(.caption2).lineLimit(2) }
        }
        .padding(6)
        .frame(width: max(80, durationHours * hourWidth), alignment: .leading)
        .background(Color.blue.opacity(0.2))
        .cornerRadius(6)
        .offset(x: offsetHours * hourWidth)
    }
}

// Simple player wrapper for HLS playback
public struct PlayerView: View {
    public let streamURL: URL
    @State private var player: AVPlayer?

    public init(streamURL: URL) {
        self.streamURL = streamURL
    }

    public var body: some View {
        VideoPlayer(player: player)
            .onAppear {
                if player == nil {
                    player = AVPlayer(url: streamURL)
                    player?.play()
                }
            }
            .onDisappear { player?.pause() }
    }
}
