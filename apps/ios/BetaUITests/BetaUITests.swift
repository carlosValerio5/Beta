import XCTest

final class BetaUITests: XCTestCase {
    @MainActor
    func testLaunchShowsTheThreeTabs() {
        let app = XCUIApplication()
        app.launch()
        XCTAssertTrue(app.tabBars.buttons["Climb"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.tabBars.buttons["Logbook"].exists)
        XCTAssertTrue(app.tabBars.buttons["Profile"].exists)
    }

    @MainActor
    func testCaptureScreenOffersTheLibrary() {
        let app = XCUIApplication()
        app.launch()
        XCTAssertTrue(app.buttons["Choose from library"].waitForExistence(timeout: 10))
    }
}
