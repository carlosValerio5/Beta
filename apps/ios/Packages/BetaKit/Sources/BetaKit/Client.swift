import Foundation

/// Everything the app needs from the API. `BetaClient` talks HTTP; tests use in-memory fakes.
public protocol BetaAPI: Sendable {
    func health() async throws -> Health
    func uploadAnalysis(jpeg: Data, wallHeightCm: Double?) async throws -> Analysis
    func analysis(id: String) async throws -> Analysis
    func selectProblem(analysisId: String, selection: ProblemSelection) async throws -> Analysis
    func requestBeta(analysisId: String, profile: ClimberProfile) async throws -> Beta
    func beta(id: String) async throws -> Beta
    func requestVideo(betaId: String) async throws -> Video
    func video(id: String) async throws -> Video
    func sendFeedback(betaId: String, kind: FeedbackKind, moveIndex: Int?, note: String) async throws -> FeedbackReceipt
}

public struct APIError: Error, Equatable, Sendable, LocalizedError {
    public let status: Int
    public let code: String
    public let message: String

    public init(status: Int, code: String, message: String) {
        self.status = status
        self.code = code
        self.message = message
    }

    public var errorDescription: String? { message.isEmpty ? "Request failed (\(status))" : message }
}

public struct MultipartForm: Sendable {
    public let boundary: String
    private var parts = Data()

    public init(boundary: String = "Beta-\(UUID().uuidString)") {
        self.boundary = boundary
    }

    public mutating func addField(name: String, value: String) {
        parts.append(Data("--\(boundary)\r\nContent-Disposition: form-data; name=\"\(name)\"\r\n\r\n\(value)\r\n".utf8))
    }

    public mutating func addFile(name: String, filename: String, contentType: String, data: Data) {
        parts.append(Data("--\(boundary)\r\n".utf8))
        parts.append(Data("Content-Disposition: form-data; name=\"\(name)\"; filename=\"\(filename)\"\r\n".utf8))
        parts.append(Data("Content-Type: \(contentType)\r\n\r\n".utf8))
        parts.append(data)
        parts.append(Data("\r\n".utf8))
    }

    public var body: Data { parts + Data("--\(boundary)--\r\n".utf8) }
    public var contentType: String { "multipart/form-data; boundary=\(boundary)" }
}

public final class BetaClient: BetaAPI, Sendable {
    public let baseURL: URL
    public let deviceId: String
    private let session: URLSession

    public init(baseURL: URL, deviceId: String, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.deviceId = deviceId
        self.session = session
    }

    public func health() async throws -> Health {
        try await send(request("GET", "/health"))
    }

    public func uploadAnalysis(jpeg: Data, wallHeightCm: Double?) async throws -> Analysis {
        var form = MultipartForm()
        form.addFile(name: "image", filename: "photo.jpg", contentType: "image/jpeg", data: jpeg)
        if let wallHeightCm { form.addField(name: "wall_height_cm", value: String(format: "%.0f", wallHeightCm)) }
        return try await send(request("POST", "/v1/analyses", body: form.body, contentType: form.contentType))
    }

    public func analysis(id: String) async throws -> Analysis {
        try await send(request("GET", "/v1/analyses/\(id)"))
    }

    public func selectProblem(analysisId: String, selection: ProblemSelection) async throws -> Analysis {
        try await send(request("PUT", "/v1/analyses/\(analysisId)/problem", json: selection))
    }

    public func requestBeta(analysisId: String, profile: ClimberProfile) async throws -> Beta {
        try await send(request("POST", "/v1/analyses/\(analysisId)/betas", json: BetaRequestBody(profile: profile)))
    }

    public func beta(id: String) async throws -> Beta {
        try await send(request("GET", "/v1/betas/\(id)"))
    }

    public func requestVideo(betaId: String) async throws -> Video {
        try await send(request("POST", "/v1/betas/\(betaId)/videos"))
    }

    public func video(id: String) async throws -> Video {
        try await send(request("GET", "/v1/videos/\(id)"))
    }

    public func sendFeedback(betaId: String, kind: FeedbackKind, moveIndex: Int?, note: String) async throws -> FeedbackReceipt {
        try await send(
            request("POST", "/v1/betas/\(betaId)/feedback", json: FeedbackBody(kind: kind, moveIndex: moveIndex, note: note))
        )
    }

    // MARK: - plumbing

    private func request(_ method: String, _ path: String, body: Data? = nil, contentType: String? = nil) -> URLRequest {
        var request = URLRequest(url: baseURL.appending(path: path))
        request.httpMethod = method
        request.setValue(deviceId, forHTTPHeaderField: "X-Device-Id")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let contentType { request.setValue(contentType, forHTTPHeaderField: "Content-Type") }
        request.httpBody = body
        return request
    }

    private func request(_ method: String, _ path: String, json: some Encodable) throws -> URLRequest {
        request(method, path, body: try BetaJSON.encoder.encode(json), contentType: "application/json")
    }

    private func send<T: Decodable>(_ request: URLRequest) async throws -> T {
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw APIError(status: -1, code: "no_response", message: "No response from the server.")
        }
        guard (200..<300).contains(http.statusCode) else { throw Self.error(status: http.statusCode, data: data) }
        return try BetaJSON.decoder.decode(T.self, from: data)
    }

    private func send<T: Decodable>(_ request: () throws -> URLRequest) async throws -> T {
        try await send(try request())
    }

    static func error(status: Int, data: Data) -> APIError {
        struct Envelope: Decodable { struct Body: Decodable { let code: String; let message: String }; let error: Body }
        if let envelope = try? JSONDecoder().decode(Envelope.self, from: data) {
            return APIError(status: status, code: envelope.error.code, message: envelope.error.message)
        }
        return APIError(status: status, code: "http_\(status)", message: String(decoding: data.prefix(200), as: UTF8.self))
    }
}
