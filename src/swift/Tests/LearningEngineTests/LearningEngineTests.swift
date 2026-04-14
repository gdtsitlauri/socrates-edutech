import Foundation
import XCTest
@testable import LearningEngine

final class LearningEngineTests: XCTestCase {
    func testSpacedRepetition() {
        let engine = LearningEngine()
        let formatter = ISO8601DateFormatter()
        let lastReview = formatter.date(from: "2026-04-01T00:00:00Z")!

        let first = engine.scheduleReview(
            lastReview: lastReview,
            intervalDays: 1,
            easeFactor: 2.5,
            quality: 5,
            repetitions: 1
        )

        let second = engine.scheduleReview(
            lastReview: first.nextReview,
            intervalDays: first.intervalDays,
            easeFactor: first.easeFactor,
            quality: 5,
            repetitions: first.repetitions
        )

        XCTAssertGreaterThanOrEqual(first.intervalDays, 6)
        XCTAssertGreaterThan(second.intervalDays, first.intervalDays)
    }

    func testKnowledgeGraphRecommendationOrder() {
        let engine = LearningEngine()
        let path = engine.recommendPath(
            target: "modeling",
            mastery: [
                "numeracy": 0.61,
                "fractions": 0.42,
                "equations": 0.35,
                "functions": 0.18,
                "systems": 0.24,
                "modeling": 0.11
            ],
            graph: [
                "fractions": ["numeracy"],
                "equations": ["fractions"],
                "functions": ["equations"],
                "systems": ["equations"],
                "modeling": ["functions", "systems"]
            ]
        )

        XCTAssertEqual(Array(path.prefix(3)), ["numeracy", "fractions", "equations"])
        XCTAssertEqual(path.last, "modeling")
    }

    func testProgressSchemaDecoding() throws {
        let engine = LearningEngine()
        let json = """
        {
          "student_id": 1,
          "course_id": 1,
          "learning_style": "causal-visual",
          "concept_mastery": {
            "numeracy": 0.62,
            "fractions": 0.48
          },
          "recent_scores": [92, 81, 88],
          "upcoming_reviews": [
            {
              "concept_id": "fractions",
              "due_on": "2026-04-16",
              "interval_days": 2,
              "ease_factor": 2.4
            }
          ],
          "updated_at": "2026-04-14T18:00:00Z"
        }
        """

        let snapshot = try engine.decodeProgress(data: Data(json.utf8))
        XCTAssertEqual(snapshot.studentId, 1)
        XCTAssertEqual(snapshot.upcomingReviews.first?.conceptId, "fractions")
    }
}
