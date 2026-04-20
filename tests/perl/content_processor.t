use strict;
use warnings;
use Test::More;
use JSON::PP;
use FindBin qw($Bin);
use File::Spec;

my $root = File::Spec->catdir($Bin, '..', '..');
my $script = File::Spec->catfile($root, 'src', 'perl', 'content_processor.pl');
require $script;

my $sample = <<'MARKDOWN';
# Linear Equations
Definition: An equation states that two expressions are equal.
Equation: $2x + 3 = 11$
\[
x = 4
\]
MARKDOWN

my $analysis = analyze_content($sample);

ok($analysis->{terms}->{Linear} >= 1, 'extracts heading terms');
ok(@{$analysis->{definitions}} >= 1, 'extracts definitions');
ok(@{$analysis->{formulas}} >= 2, 'extracts inline and block formulas');
ok($analysis->{flexible_match_example}, 'flexible answer match stays true');
ok(answers_match('\frac{3}{4}', '3/4'), 'normalizes simple LaTeX fractions');

done_testing();
