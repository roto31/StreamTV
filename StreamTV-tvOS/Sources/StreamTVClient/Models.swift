import Foundation

public struct Channel: Identifiable, Hashable {
    public let id: String           // channel number/id
    public let name: String
    public let group: String?
    public let logoURL: URL?
    public let streamURL: URL
}

public struct Programme: Identifiable, Hashable {
    public let id: String
    public let channelId: String
    public let title: String
    public let subtitle: String?
    public let desc: String?
    public let start: Date
    public let end: Date
}

public final class AppState: ObservableObject {
    @Published public var channels: [Channel] = []
    @Published public var programmesByChannel: [String: [Programme]] = [:]
    @Published public var baseURL: URL?
    @Published public var accessToken: String?

    public init(baseURL: URL? = nil, accessToken: String? = nil) {
        self.baseURL = baseURL
        self.accessToken = accessToken
    }
}
