package socrates.mobile

import kotlin.coroutines.Continuation
import kotlin.coroutines.EmptyCoroutineContext
import kotlin.coroutines.startCoroutine
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

private fun runSuspend(block: suspend () -> Unit) {
    var failure: Throwable? = null
    block.startCoroutine(object : Continuation<Unit> {
        override val context = EmptyCoroutineContext

        override fun resumeWith(result: Result<Unit>) {
            failure = result.exceptionOrNull()
        }
    })
    failure?.let { throw it }
}

class QuizEngineTest {
    fun testAdaptiveDifficulty() {
        val engine = QuizEngine(
            mutableListOf(
                Question("easy", "2 + 2", -1.0),
                Question("medium", "Solve 2x + 1 = 9", 0.1),
                Question("hard", "Differentiate x^3", 1.3)
            )
        )

        val theta = 0.2
        val question = engine.selectNextQuestion(theta)

        assertTrue(question?.id == "medium")
    }

    fun testAbilityUpdateMovesTowardCorrectResponse() {
        val engine = QuizEngine()
        val question = Question("medium", "Solve 2x + 1 = 9", 0.1, 1.2)

        val updated = engine.updateAbility(theta = 0.0, question = question, correct = true)

        assertTrue(updated > 0.0)
    }

    fun testCoroutineLoadingReplacesQuestionBank() {
        runSuspend {
            val engine = QuizEngine()
            engine.loadQuestions {
                listOf(
                    Question("algebra", "2 + 2", -0.8),
                    Question("functions", "Evaluate f(2)", 0.4)
                )
            }

            val question = engine.selectNextQuestion(theta = 0.35)
            assertNotNull(question)
            assertTrue(question.id == "functions")
        }
    }
}
