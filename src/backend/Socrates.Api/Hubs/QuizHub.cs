using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.SignalR;

namespace Socrates.Api.Hubs;

[Authorize]
public class QuizHub : Hub
{
    public async Task SubmitScore(string studentName, int score)
    {
        await Clients.All.SendAsync("LeaderboardUpdated", new
        {
            studentName,
            score,
            submittedAtUtc = DateTime.UtcNow
        });
    }

    public async Task BroadcastFeedback(int assessmentId, bool isCorrect)
    {
        await Clients.All.SendAsync("FeedbackReceived", new
        {
            assessmentId,
            isCorrect,
            message = isCorrect ? "Correct response." : "Review the prerequisite concept chain."
        });
    }
}
