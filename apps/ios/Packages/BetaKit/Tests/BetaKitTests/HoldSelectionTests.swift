import Testing
@testable import BetaKit

@Suite struct HoldSelectionTests {
    @Test func selectingAColourPicksItsHoldsAndSuggestsStartAndTop() {
        var selection = HoldSelection(holds: Fixtures.holds)
        selection.selectColor("yellow")
        #expect(selection.selected == [0, 1, 2, 3, 4, 5])
        #expect(selection.topId == 5)
        #expect(selection.startIds == [0, 1])  // lowest *hand-sized* holds; tiny footholds skipped
        #expect(selection.isComplete)
    }

    @Test func tapTogglesMembershipInPickMode() {
        var selection = HoldSelection(holds: Fixtures.holds)
        selection.selectColor("yellow")
        selection.tap(holdId: 6)
        #expect(selection.selected.contains(6))
        selection.tap(holdId: 6)
        #expect(!selection.selected.contains(6))
    }

    @Test func removingAHoldClearsItsRole() {
        var selection = HoldSelection(holds: Fixtures.holds)
        selection.selectColor("yellow")
        selection.tap(holdId: 5)
        #expect(selection.topId == nil)
        #expect(!selection.isComplete)
    }

    @Test func startModeKeepsAtMostTwoStarts() {
        var selection = HoldSelection(holds: Fixtures.holds)
        selection.selectColor("yellow")
        selection.mode = .start
        selection.tap(holdId: 4)
        #expect(selection.startIds == [1, 4])
        #expect(selection.selected.contains(4))
    }

    @Test func topCannotAlsoBeAStart() {
        var selection = HoldSelection(holds: Fixtures.holds)
        selection.selectColor("yellow")
        selection.mode = .top
        selection.tap(holdId: 0)
        #expect(selection.topId == 0)
        #expect(!selection.startIds.contains(0))
    }

    @Test func hitTestingFindsTheNearestHold() {
        let selection = HoldSelection(holds: Fixtures.holds)
        #expect(selection.hold(atX: 452, y: 1048)?.id == 0)
        #expect(selection.hold(atX: 900, y: 100) == nil)
    }

    @Test func payloadCarriesColourOnlyWhenUniform() throws {
        var selection = HoldSelection(holds: Fixtures.holds)
        selection.selectColor("yellow")
        let uniform = try #require(selection.problemSelection)
        #expect(uniform.color == "yellow")
        #expect(uniform.holdIds == [0, 1, 2, 3, 4, 5])

        selection.tap(holdId: 6)
        let mixed = try #require(selection.problemSelection)
        #expect(mixed.color == nil)
    }
}
