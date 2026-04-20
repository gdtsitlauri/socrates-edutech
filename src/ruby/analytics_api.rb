require "json"
require "sinatra/base"

class AnalyticsApi < Sinatra::Base
  set :bind, "0.0.0.0"
  set :port, 4567
  set :protection, except: :host_authorization

  COMPLETION_RATES = [
    { course: "Adaptive Algebra", completion_rate: 0.84, active_students: 118 },
    { course: "Numerical Methods", completion_rate: 0.72, active_students: 64 }
  ].freeze

  TIME_ON_TASK = [
    { course: "Adaptive Algebra", mean_minutes: 34.2, p90_minutes: 55.1 },
    { course: "Numerical Methods", mean_minutes: 41.8, p90_minutes: 67.3 }
  ].freeze

  before do
    content_type :json
  end

  get "/health" do
    JSON.pretty_generate(status: "ok", service: "ruby-analytics")
  end

  get "/analytics/completion_rates" do
    JSON.pretty_generate(completion_rates: COMPLETION_RATES)
  end

  get "/analytics/time_on_task" do
    JSON.pretty_generate(time_on_task: TIME_ON_TASK)
  end

  get "/analytics/overview" do
    average_completion = COMPLETION_RATES.sum { |item| item[:completion_rate] } / COMPLETION_RATES.length
    average_time = TIME_ON_TASK.sum { |item| item[:mean_minutes] } / TIME_ON_TASK.length

    JSON.pretty_generate(
      average_completion_rate: average_completion.round(3),
      average_time_on_task_minutes: average_time.round(2)
    )
  end
end

AnalyticsApi.run! if $PROGRAM_NAME == __FILE__
