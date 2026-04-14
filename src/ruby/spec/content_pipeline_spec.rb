require_relative "spec_helper"
require_relative "../content_pipeline"

RSpec.describe ContentPipeline do
  it "builds html, toc, and readability metrics" do
    markdown = <<~MD
      # Linear Equations

      Definition: Two expressions are equal.

      Further reading: [OpenStax](https://openstax.org/subjects/math)
    MD

    result = described_class.new.run(markdown)

    expect(result[:html]).to include("<h1>Linear Equations</h1>")
    expect(result[:table_of_contents].first[:anchor]).to eq("linear-equations")
    expect(result[:links].first[:valid_scheme]).to eq(true)
    expect(result[:readability][:flesch_kincaid]).to be_a(Float)
  end
end
