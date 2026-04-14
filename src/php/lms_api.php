<?php
declare(strict_types=1);

header('Content-Type: application/json');

$courses = [
    1 => [
        'id' => 1,
        'title' => 'Adaptive Algebra',
        'modules' => ['numeracy', 'fractions', 'equations', 'functions', 'systems', 'modeling'],
        'prerequisites' => [],
    ],
    2 => [
        'id' => 2,
        'title' => 'Numerical Methods',
        'modules' => ['matrix_ops', 'ode_solvers', 'eigenvalues'],
        'prerequisites' => ['Adaptive Algebra'],
    ],
];

$students = [
    1 => ['id' => 1, 'name' => 'Ada Student', 'learning_style' => 'causal-visual'],
];

$gradebook = [
    1 => [
        ['assignment' => 'quiz_1', 'weight' => 0.20, 'score' => 92],
        ['assignment' => 'midterm', 'weight' => 0.35, 'score' => 81],
        ['assignment' => 'project', 'weight' => 0.45, 'score' => 88],
    ],
];

function json_response(array $payload, int $status = 200): void
{
    http_response_code($status);
    echo json_encode($payload, JSON_PRETTY_PRINT);
    exit;
}

function weighted_grade(array $entries): float
{
    $total = 0.0;
    foreach ($entries as $entry) {
        $total += $entry['weight'] * $entry['score'];
    }
    return round($total, 2);
}

$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?? '/';
$method = $_SERVER['REQUEST_METHOD'];
$segments = array_values(array_filter(explode('/', trim($path, '/'))));
$body = json_decode(file_get_contents('php://input') ?: 'null', true) ?: [];

if ($path === '/health') {
    json_response(['status' => 'ok', 'service' => 'php-lms']);
}

if ($method === 'GET' && $segments === ['courses']) {
    json_response(['courses' => array_values($courses)]);
}

if ($method === 'GET' && count($segments) === 2 && $segments[0] === 'courses') {
    $courseId = (int) $segments[1];
    if (!isset($courses[$courseId])) {
        json_response(['error' => 'course not found'], 404);
    }
    json_response($courses[$courseId]);
}

if ($method === 'GET' && count($segments) === 3 && $segments[0] === 'courses' && $segments[2] === 'recommendations') {
    $courseId = (int) $segments[1];
    if (!isset($courses[$courseId])) {
        json_response(['error' => 'course not found'], 404);
    }

    $recommendations = [];
    foreach ($courses[$courseId]['modules'] as $index => $module) {
        $recommendations[] = [
            'concept_id' => $module,
            'priority' => round(1.0 / ($index + 1), 3),
            'difficulty' => $index < 2 ? 'foundational' : 'core',
        ];
    }

    json_response([
        'course_id' => $courseId,
        'recommendations' => $recommendations,
    ]);
}

if ($method === 'GET' && count($segments) === 3 && $segments[0] === 'courses' && $segments[2] === 'catalog') {
    $courseId = (int) $segments[1];
    if (!isset($courses[$courseId])) {
        json_response(['error' => 'course not found'], 404);
    }

    json_response([
        'course' => $courses[$courseId],
        'catalog_entry' => [
            'credits' => 5,
            'delivery_mode' => 'blended',
            'enrollment_open' => true,
        ],
    ]);
}

if ($method === 'POST' && $segments === ['enrollments']) {
    if (!isset($students[(int) ($body['student_id'] ?? 0)], $courses[(int) ($body['course_id'] ?? 0)])) {
        json_response(['error' => 'unknown student or course'], 422);
    }

    json_response([
        'status' => 'enrolled',
        'student_id' => (int) $body['student_id'],
        'course_id' => (int) $body['course_id'],
    ], 201);
}

if ($method === 'GET' && count($segments) === 3 && $segments[0] === 'students' && $segments[2] === 'gradebook') {
    $studentId = (int) $segments[1];
    if (!isset($gradebook[$studentId])) {
        json_response(['error' => 'gradebook not found'], 404);
    }

    json_response([
        'student_id' => $studentId,
        'entries' => $gradebook[$studentId],
        'weighted_grade' => weighted_grade($gradebook[$studentId]),
    ]);
}

if ($method === 'GET' && count($segments) === 3 && $segments[0] === 'students' && $segments[2] === 'progress') {
    $studentId = (int) $segments[1];
    if (!isset($students[$studentId])) {
        json_response(['error' => 'student not found'], 404);
    }

    json_response([
        'student_id' => $studentId,
        'course_id' => 1,
        'learning_style' => $students[$studentId]['learning_style'],
        'concept_mastery' => [
            'numeracy' => 0.62,
            'fractions' => 0.48,
            'equations' => 0.57,
            'functions' => 0.33,
        ],
        'recent_scores' => [92, 81, 88],
        'upcoming_reviews' => [
            [
                'concept_id' => 'fractions',
                'due_on' => '2026-04-16',
                'interval_days' => 2,
                'ease_factor' => 2.4,
            ],
        ],
        'updated_at' => '2026-04-14T18:00:00Z',
    ]);
}

json_response(['error' => 'route not found', 'path' => $path], 404);
