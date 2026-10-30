import Foundation
import Testing
@testable import BetaKit

/// URLProtocol stub: tests set `handler`, the client's URLSession routes every request here.
final class StubURLProtocol: URLProtocol, @unchecked Sendable {
    nonisolated(unsafe) static var handler: ((URLRequest, Data) -> (Int, Data))?
    nonisolated(unsafe) static var requests: [(URLRequest, Data)] = []

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        let body = Self.body(of: request)
        Self.requests.append((request, body))
        let (status, data) = Self.handler?(request, body) ?? (500, Data())
        let response = HTTPURLResponse(
            url: request.url!, statusCode: status, httpVersion: nil,
            headerFields: ["Content-Type": "application/json"]
        )!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: data)
        client?.urlProtocolDidFinishLoading(self)
    }

    override func stopLoading() {}

    static func body(of request: URLRequest) -> Data {
        if let body = request.httpBody { return body }
        guard let stream = request.httpBodyStream else { return Data() }
        stream.open()
        defer { stream.close() }
        var data = Data()
        var buffer = [UInt8](repeating: 0, count: 4096)
        while stream.hasBytesAvailable {
            let n = stream.read(&buffer, maxLength: buffer.count)
            if n <= 0 { break }
            data.append(buffer, count: n)
        }
        return data
    }
}

func stubbedClient() -> BetaClient {
    let config = URLSessionConfiguration.ephemeral
    config.protocolClasses = [StubURLProtocol.self]
    return BetaClient(
        baseURL: URL(string: "http://localhost:8000")!,
        deviceId: "dev_ios_test",
        session: URLSession(configuration: config)
    )
}

@Suite(.serialized) struct ClientTests {
    init() {
        StubURLProtocol.requests = []
        StubURLProtocol.handler = nil
    }

    @Test func uploadSendsMultipartWithDeviceId() async throws {
        let example = try Fixtures.contract("api/examples/analysis.json")
        StubURLProtocol.handler = { _, _ in (201, example) }

        let analysis = try await stubbedClient().uploadAnalysis(jpeg: Data([0xFF, 0xD8, 0x01]), wallHeightCm: 450)

        #expect(!analysis.holds.isEmpty)
        let (request, body) = try #require(StubURLProtocol.requests.first)
        #expect(request.httpMethod == "POST")
        #expect(request.url?.path == "/v1/analyses")
        #expect(request.value(forHTTPHeaderField: "X-Device-Id") == "dev_ios_test")
        #expect(request.value(forHTTPHeaderField: "Content-Type")?.hasPrefix("multipart/form-data; boundary=") == true)
        let text = String(decoding: body, as: UTF8.self)
        #expect(text.contains("name=\"image\"; filename=\"photo.jpg\""))
        #expect(text.contains("name=\"wall_height_cm\""))
        #expect(text.contains("450"))
    }

    @Test func apiErrorsAreDecoded() async throws {
        StubURLProtocol.handler = { _, _ in
            (409, Data(#"{"error": {"code": "invalid_state", "message": "select a problem first"}}"#.utf8))
        }
        await #expect(throws: APIError(status: 409, code: "invalid_state", message: "select a problem first")) {
            try await stubbedClient().requestBeta(
                analysisId: "ana_1",
                profile: ClimberProfile(heightCm: 175, apeIndexCm: 0, maxGrade: "V3", style: .balanced)
            )
        }
    }

    @Test func requestBetaPostsTheProfile() async throws {
        let example = try Fixtures.contract("api/examples/beta.json")
        StubURLProtocol.handler = { _, _ in (202, example) }
        _ = try await stubbedClient().requestBeta(
            analysisId: "ana_1",
            profile: ClimberProfile(heightCm: 168, apeIndexCm: 3, maxGrade: "V5", style: .static)
        )
        let (request, body) = try #require(StubURLProtocol.requests.first)
        #expect(request.url?.path == "/v1/analyses/ana_1/betas")
        let json = try JSONSerialization.jsonObject(with: body) as? [String: [String: Any]]
        #expect(json?["profile"]?["height_cm"] as? Double == 168)
    }

    @Test func multipartBodyIsWellFormed() {
        var form = MultipartForm(boundary: "XYZ")
        form.addField(name: "a", value: "1")
        form.addFile(name: "image", filename: "photo.jpg", contentType: "image/jpeg", data: Data([1, 2]))
        let text = String(decoding: form.body, as: UTF8.self)
        #expect(text.hasPrefix("--XYZ\r\n"))
        #expect(text.hasSuffix("--XYZ--\r\n"))
        #expect(text.contains("Content-Type: image/jpeg\r\n\r\n"))
        #expect(form.contentType == "multipart/form-data; boundary=XYZ")
    }
}

@Suite struct PollingTests {
    actor Recorder {
        var sleeps: [Duration] = []
        var calls = 0
        func sleep(_ d: Duration) { sleeps.append(d) }
        func next() -> Int { calls += 1; return calls }
    }

    @Test func returnsOnceDoneAndBacksOff() async throws {
        let recorder = Recorder()
        let poller = Poller(initial: .milliseconds(500), maxInterval: .seconds(2), timeout: .seconds(60)) {
            await recorder.sleep($0)
        }
        let value = try await poller.poll(fetch: { await recorder.next() }, until: { $0 >= 4 })
        #expect(value == 4)
        let sleeps = await recorder.sleeps
        #expect(sleeps.count == 3)
        #expect(sleeps == sleeps.sorted())
        #expect(sleeps.allSatisfy { $0 <= .seconds(2) })
    }

    @Test func timesOut() async {
        let recorder = Recorder()
        let poller = Poller(initial: .seconds(1), maxInterval: .seconds(1), timeout: .seconds(3)) {
            await recorder.sleep($0)
        }
        await #expect(throws: PollingError.timedOut) {
            try await poller.poll(fetch: { await recorder.next() }, until: { _ in false })
        }
    }
}
