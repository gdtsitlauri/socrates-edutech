package socrates.mobile

fun main() {
    val suite = QuizEngineTest()
    suite.testAdaptiveDifficulty()
    suite.testAbilityUpdateMovesTowardCorrectResponse()
    suite.testCoroutineLoadingReplacesQuestionBank()
    println("Kotlin QuizEngine tests passed.")
}
