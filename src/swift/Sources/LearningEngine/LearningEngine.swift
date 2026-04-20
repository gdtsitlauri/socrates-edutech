import Foundation

public struct UpcomingReviewPayload: Codable, Equatable {
    public let conceptId: String
    public let dueOn: String
    public let intervalDays: Int
    public let easeFactor: Double
}

public struct StudentProgressSnapshot: Codable, Equatable {
    public let studentId: Int
    public let courseId: Int
    public let learningStyle: String
    public let conceptMastery: [String: Double]
    public let recentScores: [Double]
    public let upcomingReviews: [UpcomingReviewPayload]
    public let updatedAt: String
}

public struct ReviewSchedule: Equatable {
    public let nextReview: Date
    public let intervalDays: Int
    public let easeFactor: Double
    public let repetitions: Int
}

private extension Sequence where Element: Hashable {
    func uniquedStable() -> [Element] {
        var seen = Set<Element>()
        var ordered: [Element] = []
        for element in self {
            if seen.insert(element).inserted {
                ordered.append(element)
            }
        }
        return ordered
    }
}

public final class LearningEngine {
    public init() {}

    public func scheduleReview(
        lastReview: Date,
        intervalDays: Int,
        easeFactor: Double,
        quality: Int,
        repetitions: Int
    ) -> ReviewSchedule {
        let boundedQuality = max(0, min(5, quality))
        let updatedEase = max(
            1.3,
            easeFactor + (0.1 - Double(5 - boundedQuality) * (0.08 + Double(5 - boundedQuality) * 0.02))
        )

        let nextInterval: Int
        let nextRepetitions: Int
        if boundedQuality < 3 {
            nextInterval = 1
            nextRepetitions = 0
        } else if repetitions == 0 {
            nextInterval = 1
            nextRepetitions = 1
        } else if repetitions == 1 {
            nextInterval = 6
            nextRepetitions = 2
        } else {
            nextInterval = max(1, Int((Double(intervalDays) * easeFactor).rounded()))
            nextRepetitions = repetitions + 1
        }

        let nextReview = Calendar.current.date(byAdding: .day, value: nextInterval, to: lastReview) ?? lastReview
        return ReviewSchedule(
            nextReview: nextReview,
            intervalDays: nextInterval,
            easeFactor: updatedEase,
            repetitions: nextRepetitions
        )
    }

    public func recommendPath(
        target: String,
        mastery: [String: Double],
        graph: [String: [String]],
        threshold: Double = 0.72
    ) -> [String] {
        var ordered: [String] = []
        var seen = Set<String>()
        visit(target: target, mastery: mastery, graph: graph, threshold: threshold, ordered: &ordered, seen: &seen)
        return ordered.uniquedStable()
    }

    private func visit(
        target: String,
        mastery: [String: Double],
        graph: [String: [String]],
        threshold: Double,
        ordered: inout [String],
        seen: inout Set<String>
    ) {
        guard !seen.contains(target) else { return }
        seen.insert(target)

        for prereq in graph[target, default: []] {
            visit(target: prereq, mastery: mastery, graph: graph, threshold: threshold, ordered: &ordered, seen: &seen)
        }

        if mastery[target, default: 0.0] < threshold {
            ordered.append(target)
        }
    }

    public func decodeProgress(data: Data) throws -> StudentProgressSnapshot {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(StudentProgressSnapshot.self, from: data)
    }
}
