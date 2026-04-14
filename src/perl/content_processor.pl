#!/usr/bin/env perl
use strict;
use warnings;
use JSON::PP;

sub _record_terms_from_phrase {
    my ($counts, $phrase) = @_;
    for my $term (grep { length($_) > 2 } split /\W+/, $phrase // '') {
        next unless $term =~ /^[A-Za-z]/;
        $counts->{$term}++;
    }
}

sub extract_terms {
    my ($text) = @_;
    my %counts;

    while ($text =~ /^(#+)\s+(.+)$/mg) {
        _record_terms_from_phrase(\%counts, $2);
    }

    while ($text =~ /\\(?:section|subsection)\{([^}]+)\}/g) {
        _record_terms_from_phrase(\%counts, $1);
    }

    while ($text =~ /<h[1-6][^>]*>(.*?)<\/h[1-6]>/sg) {
        my $heading = $1;
        $heading =~ s/<[^>]+>//g;
        _record_terms_from_phrase(\%counts, $heading);
    }

    while ($text =~ /\b([A-Z][A-Za-z0-9_-]{2,})\b/g) {
        $counts{$1}++;
    }

    return \%counts;
}

sub extract_definitions {
    my ($text) = @_;
    my @definitions;

    while ($text =~ /(?:Definition|Term)\s*:\s*([^<\n]+)/g) {
        push @definitions, {
            term => 'Definition',
            definition => $1,
        };
    }

    while ($text =~ /([A-Za-z][A-Za-z0-9 _-]+):\s*([^<\n]+)/g) {
        next if $1 =~ /^(Definition|Term)$/;
        push @definitions, {
            term => $1,
            definition => $2,
        };
    }

    return \@definitions;
}

sub extract_formulas {
    my ($text) = @_;
    my @formulas;

    while ($text =~ /\$([^\$]+)\$/g) {
        push @formulas, $1;
    }

    while ($text =~ /\\\[(.*?)\\\]/sg) {
        push @formulas, $1;
    }

    while ($text =~ /<math>(.*?)<\/math>/sg) {
        push @formulas, $1;
    }

    return \@formulas;
}

sub generate_flashcards {
    my ($definitions, $formulas) = @_;
    my @flashcards = map {
        {
            prompt => "Define " . $_->{term},
            answer => $_->{definition},
        }
    } @$definitions;

    push @flashcards, map {
        {
            prompt => "Interpret the formula",
            answer => $_,
        }
    } @$formulas;

    return \@flashcards;
}

sub answers_match {
    my ($expected, $actual) = @_;
    for ($expected, $actual) {
        $_ = lc($_ // '');
        s/\\frac\{([^}]+)\}\{([^}]+)\}/$1\/$2/g;
        s/[[:space:]]+//g;
        s/[()]//g;
    }
    return $expected eq $actual;
}

sub analyze_content {
    my ($text) = @_;
    my $terms = extract_terms($text);
    my $definitions = extract_definitions($text);
    my $formulas = extract_formulas($text);
    my $flashcards = generate_flashcards($definitions, $formulas);

    return {
        terms => $terms,
        definitions => $definitions,
        formulas => $formulas,
        flashcards => $flashcards,
        flexible_match_example => answers_match("3/4", " 3 / 4 "),
    };
}

sub main {
    my ($input_path) = @_;
    die "usage: perl content_processor.pl input.md\n" unless $input_path;

    open my $handle, '<', $input_path or die "cannot open $input_path: $!\n";
    local $/ = undef;
    my $text = <$handle>;
    close $handle;

    print JSON::PP->new->pretty->encode(analyze_content($text));
    return 0;
}

unless (caller) {
    exit main(@ARGV);
}

1;
