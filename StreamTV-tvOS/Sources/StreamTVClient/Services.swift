import Foundation

// MARK: - Networking helpers with simple retry

struct RetryPolicy {
    let maxAttempts: Int
    let baseDelay: TimeInterval
    static let `default` = RetryPolicy(maxAttempts: 3, baseDelay: 0.5)
}

func withRetry<T>(_ policy: RetryPolicy = .default, operation: @escaping () async throws -> T) async throws -> T {
    var attempt = 0
    var lastError: Error?
    while attempt < policy.maxAttempts {
        do { return try await operation() }
        catch {
            lastError = error
            attempt += 1
            if attempt >= policy.maxAttempts { break }
            try await Task.sleep(nanoseconds: UInt64(policy.baseDelay * pow(2, Double(attempt)) * 1_000_000_000))
        }
    }
    throw lastError ?? NSError(domain: "Retry", code: -1)
}

// MARK: - M3U

public final class M3UService {
    public init() {}

    public func fetchChannels(baseURL: URL, token: String?) async throws -> [Channel] {
        let m3uURL = baseURL.appendingPathComponent("iptv/channels.m3u")
        return try await withRetry {
            let (data, _) = try await URLSession.shared.data(from: m3uURL)
            return try M3UParser().parse(data: data, baseURL: baseURL, token: token)
        }
    }
}

public final class M3UParser {
    public init() {}

    public func parse(data: Data, baseURL: URL, token: String?) throws -> [Channel] {
        guard let text = String(data: data, encoding: .utf8) else { return [] }
        var channels: [Channel] = []
        let lines = text.split(separator: "\n")
        var currentAttrs: [String:String] = [:]
        for line in lines {
            if line.hasPrefix("#EXTINF:") {
                currentAttrs = parseExtInf(String(line))
            } else if line.hasPrefix("http") || line.hasPrefix("/") {
                guard let url = URL(string: String(line), relativeTo: baseURL) else { continue }
                let id = currentAttrs["tvg-id"] ?? ""
                let name = currentAttrs["tvg-name"] ?? currentAttrs["name"] ?? id
                let logo = currentAttrs["tvg-logo"].flatMap(URL.init(string:))
                let group = currentAttrs["group-title"]
                channels.append(Channel(id: id, name: name, group: group, logoURL: logo, streamURL: url))
                currentAttrs = [:]
            }
        }
        return channels
    }

    private func parseExtInf(_ line: String) -> [String:String] {
        var result: [String:String] = [:]
        let pattern = #"([\w-]+)=\"([^\"]*)\""#
        let regex = try? NSRegularExpression(pattern: pattern)
        let ns = line as NSString
        regex?.matches(in: line, range: NSRange(location: 0, length: ns.length)).forEach { m in
            let key = ns.substring(with: m.range(at: 1))
            let val = ns.substring(with: m.range(at: 2))
            result[key] = val
        }
        if let commaRange = line.range(of: ",") {
            let name = line[line.index(after: commaRange.lowerBound)...].trimmingCharacters(in: .whitespaces)
            if !name.isEmpty { result["name"] = name }
        }
        return result
    }
}

// MARK: - XMLTV

public final class XMLTVService {
    public init() {}

    public func fetchProgrammes(baseURL: URL) async throws -> [Programme] {
        let url = baseURL.appendingPathComponent("iptv/xmltv.xml")
        return try await withRetry {
            let (data, _) = try await URLSession.shared.data(from: url)
            return try XMLTVParser().parse(data: data)
        }
    }
}

public final class XMLTVParser: NSObject, XMLParserDelegate {
    private var programmes: [Programme] = []
    private var currentAttrs: [String:String] = [:]
    private var currentText: String = ""
    private var title: String?
    private var subtitle: String?
    private var desc: String?

    public func parse(data: Data) throws -> [Programme] {
        let parser = XMLParser(data: data)
        parser.delegate = self
        if !parser.parse() {
            throw parser.parserError ?? NSError(domain: "XMLTV", code: 1)
        }
        return programmes
    }

    public func parser(_ parser: XMLParser, didStartElement name: String, namespaceURI: String?, qualifiedName q: String?, attributes: [String : String]) {
        currentText = ""
        if name == "programme" { currentAttrs = attributes; title = nil; subtitle = nil; desc = nil }
    }

    public func parser(_ parser: XMLParser, foundCharacters string: String) { currentText += string }

    public func parser(_ parser: XMLParser, didEndElement name: String, namespaceURI: String?, qualifiedName q: String?) {
        switch name {
        case "title": title = (title ?? "") + currentText.trimmed()
        case "sub-title": subtitle = (subtitle ?? "") + currentText.trimmed()
        case "desc": desc = (desc ?? "") + currentText.trimmed()
        case "programme":
            if let channelId = currentAttrs["channel"],
               let startStr = currentAttrs["start"], let endStr = currentAttrs["stop"],
               let start = dateFromXMLTV(startStr), let end = dateFromXMLTV(endStr) {
                let id = "\(channelId)_\(start.timeIntervalSince1970)"
                let prog = Programme(id: id,
                                     channelId: channelId,
                                     title: title?.nonEmpty ?? "Programme",
                                     subtitle: subtitle?.nonEmpty,
                                     desc: desc?.nonEmpty,
                                     start: start,
                                     end: end)
                programmes.append(prog)
            }
        default: break
        }
        currentText = ""
    }

    private func dateFromXMLTV(_ s: String) -> Date? {
        // format: YYYYMMDDhhmmss +0000
        let fmt = DateFormatter()
        fmt.dateFormat = "yyyyMMddHHmmss Z"
        fmt.timeZone = TimeZone(secondsFromGMT: 0)
        return fmt.date(from: s)
    }
}

private extension String {
    func trimmed() -> String { trimmingCharacters(in: .whitespacesAndNewlines) }
    var nonEmpty: String? { let t = trimmed(); return t.isEmpty ? nil : t }
}

// MARK: - Channel Admin (create channel from URL)

public struct CreateChannelRequest: Codable {
    public let url: String
    public let source: String       // "archive" | "youtube" | "http"
    public let name: String?
    public let number: String?
    public init(url: String, source: String, name: String? = nil, number: String? = nil) {
        self.url = url; self.source = source; self.name = name; self.number = number
    }
}

public final class ChannelAdminService {
    public init() {}

    public func createChannel(baseURL: URL, token: String?, body: CreateChannelRequest) async throws {
        let endpoint = baseURL.appendingPathComponent("api/channels")
        var req = URLRequest(url: endpoint)
        req.httpMethod = "POST"
        req.addValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = token { req.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization") }
        req.httpBody = try JSONEncoder().encode(body)

        return try await withRetry {
            let (_, resp) = try await URLSession.shared.data(for: req)
            guard let http = resp as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
                throw NSError(domain: "CreateChannel", code: 1, userInfo: [NSLocalizedDescriptionKey: "Create channel failed"])
            }
        }
    }
}
