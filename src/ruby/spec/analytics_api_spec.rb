require_relative "spec_helper"
require_relative "../analytics_api"

RSpec.describe AnalyticsApi do
  def app
    AnalyticsApi
  end

  it "returns overview metrics" do
    header "Host", "localhost"
    get "/analytics/overview"

    expect(last_response).to be_ok
    expect(last_response.body).to include("average_completion_rate")
    expect(last_response.body).to include("average_time_on_task_minutes")
  end
end
