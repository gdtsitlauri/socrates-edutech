require "cgi"
require "json"
require "uri"

class ContentPipeline
  HEADING_REGEX = /^(#+)\s+(.*)$/.freeze
  LINK_REGEX = /\[([^\]]+)\]\(([^)]+)\)/.freeze

  def run(markdown)
    {
      html: markdown_to_html(markdown),
      table_of_contents: build_toc(markdown),
      links: extract_links(markdown),
      readability: readability(markdown),
      vocabulary_complexity: vocabulary_complexity(markdown)
    }
  end

  private

  def markdown_to_html(markdown)
    html = []
    in_code_block = false
    code_language = nil
    code_lines = []

    markdown.lines.each do |line|
      if line =~ /^```([\w+-]+)?\s*$/
        if in_code_block
          class_name = code_language ? " class=\"language-#{CGI.escapeHTML(code_language)}\"" : ""
          html << "<pre><code#{class_name}>#{CGI.escapeHTML(code_lines.join("\n"))}</code></pre>"
          in_code_block = false
          code_language = nil
          code_lines = []
        else
          in_code_block = true
          code_language = Regexp.last_match(1)
        end
        next
      end

      if in_code_block
        code_lines << line.chomp
        next
      end

      case line
      when HEADING_REGEX
        level = Regexp.last_match(1).length
        text = CGI.escapeHTML(Regexp.last_match(2).strip)
        html << "<h#{level}>#{text}</h#{level}>"
      when /^- (.*)$/
        html << "<li>#{CGI.escapeHTML(Regexp.last_match(1).strip)}</li>"
      when /^\s*$/
        html << ""
      else
        html << "<p>#{CGI.escapeHTML(line.strip)}</p>"
      end
    end

    html.join("\n")
  end

  def build_toc(markdown)
    markdown.lines.filter_map do |line|
      match = line.match(HEADING_REGEX)
      next unless match

      {
        level: match[1].length,
        title: match[2].strip,
        anchor: match[2].strip.downcase.gsub(/[^a-z0-9]+/, "-").gsub(/^-|-$/, "")
      }
    end
  end

  def extract_links(markdown)
    markdown.scan(LINK_REGEX).map do |label, url|
      {
        label: label,
        url: url,
        valid_scheme: %w[http https].include?(URI.parse(url).scheme)
      }
    rescue URI::InvalidURIError
      {
        label: label,
        url: url,
        valid_scheme: false
      }
    end
  end

  def readability(markdown)
    words = markdown.scan(/[A-Za-z0-9']+/)
    sentences = [markdown.split(/[.!?]+/).reject(&:empty?).length, 1].max
    syllables = words.sum { |word| approximate_syllables(word) }
    {
      flesch_kincaid: (206.835 - 1.015 * (words.length.to_f / sentences) - 84.6 * (syllables.to_f / [words.length, 1].max)).round(2),
      gunning_fog: (0.4 * ((words.length.to_f / sentences) + 100.0 * complex_word_ratio(words))).round(2)
    }
  end

  def vocabulary_complexity(markdown)
    words = markdown.scan(/[A-Za-z0-9']+/).map(&:downcase)
    unique_ratio = words.empty? ? 0.0 : words.uniq.length.to_f / words.length
    advanced_ratio = complex_word_ratio(words)
    {
      lexical_diversity: unique_ratio.round(3),
      advanced_word_ratio: advanced_ratio.round(3)
    }
  end

  def approximate_syllables(word)
    count = word.downcase.scan(/[aeiouy]+/).length
    [count, 1].max
  end

  def complex_word_ratio(words)
    return 0.0 if words.empty?

    complex = words.count { |word| approximate_syllables(word) >= 3 }
    complex.to_f / words.length
  end
end

if $PROGRAM_NAME == __FILE__
  input_path = ARGV[0]
  abort("usage: ruby content_pipeline.rb path/to/input.md") unless input_path

  markdown = File.read(input_path)
  puts JSON.pretty_generate(ContentPipeline.new.run(markdown))
end
