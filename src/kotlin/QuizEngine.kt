package socrates.mobile

import kotlin.math.abs
import kotlin.math.exp

data class Question(
    val id: String,
    val prompt: String,
    val difficulty: Double,
    val discrimination: Double = 1.0
)

class QuizEngine(
    private val questionBank: MutableList<Question> = mutableListOf()
) {
    suspend fun loadQuestions(loader: suspend () -> List<Question>) {
        questionBank.clear()
        questionBank.addAll(loader())
    }

    fun probabilityCorrect(theta: Double, difficulty: Double, discrimination: Double): Double {
        return 1.0 / (1.0 + exp(-discrimination * (theta - difficulty)))
    }

    fun selectNextQuestion(theta: Double): Question? {
        return questionBank.minByOrNull { question ->
            abs(probabilityCorrect(theta, question.difficulty, question.discrimination) - 0.5)
        }
    }

    fun updateAbility(theta: Double, question: Question, correct: Boolean, stepSize: Double = 0.35): Double {
        val probability = probabilityCorrect(theta, question.difficulty, question.discrimination)
        val residual = (if (correct) 1.0 else 0.0) - probability
        return theta + stepSize * question.discrimination * residual
    }
}
