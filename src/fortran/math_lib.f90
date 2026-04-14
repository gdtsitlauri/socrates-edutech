module math_lib
  implicit none
contains

  subroutine matrix_multiply(a, b, c, n, m, p)
    integer, intent(in) :: n, m, p
    real(8), intent(in) :: a(n, m), b(m, p)
    real(8), intent(out) :: c(n, p)
    integer :: i, j, k

    c = 0.0d0
    do i = 1, n
      do j = 1, p
        do k = 1, m
          c(i, j) = c(i, j) + a(i, k) * b(k, j)
        end do
      end do
    end do
  end subroutine matrix_multiply

  subroutine gaussian_elimination(a, b, x, n)
    integer, intent(in) :: n
    real(8), intent(inout) :: a(n, n)
    real(8), intent(inout) :: b(n)
    real(8), intent(out) :: x(n)
    integer :: i, j, k
    real(8) :: factor

    do k = 1, n - 1
      do i = k + 1, n
        if (a(k, k) == 0.0d0) cycle
        factor = a(i, k) / a(k, k)
        do j = k, n
          a(i, j) = a(i, j) - factor * a(k, j)
        end do
        b(i) = b(i) - factor * b(k)
      end do
    end do

    do i = n, 1, -1
      x(i) = b(i)
      do j = i + 1, n
        x(i) = x(i) - a(i, j) * x(j)
      end do
      if (a(i, i) /= 0.0d0) then
        x(i) = x(i) / a(i, i)
      end if
    end do
  end subroutine gaussian_elimination

  subroutine lu_decomposition(a, l, u, n)
    integer, intent(in) :: n
    real(8), intent(in) :: a(n, n)
    real(8), intent(out) :: l(n, n), u(n, n)
    integer :: i, j, k

    l = 0.0d0
    u = 0.0d0
    do i = 1, n
      l(i, i) = 1.0d0
    end do

    do j = 1, n
      do i = 1, j
        u(i, j) = a(i, j)
        do k = 1, i - 1
          u(i, j) = u(i, j) - l(i, k) * u(k, j)
        end do
      end do

      do i = j + 1, n
        l(i, j) = a(i, j)
        do k = 1, j - 1
          l(i, j) = l(i, j) - l(i, k) * u(k, j)
        end do
        if (u(j, j) /= 0.0d0) then
          l(i, j) = l(i, j) / u(j, j)
        end if
      end do
    end do
  end subroutine lu_decomposition

  subroutine qr_eigenvalues(a, eigenvalues, n, iterations)
    integer, intent(in) :: n, iterations
    real(8), intent(in) :: a(n, n)
    real(8), intent(out) :: eigenvalues(n)
    real(8) :: q(n, n), r(n, n), working(n, n)
    integer :: i, iter

    working = a
    do iter = 1, iterations
      call qr_decompose(working, q, r, n)
      working = matmul(r, q)
    end do

    do i = 1, n
      eigenvalues(i) = working(i, i)
    end do
  end subroutine qr_eigenvalues

  subroutine qr_decompose(a, q, r, n)
    integer, intent(in) :: n
    real(8), intent(in) :: a(n, n)
    real(8), intent(out) :: q(n, n), r(n, n)
    real(8) :: v(n), norm_v
    integer :: i, j

    q = 0.0d0
    r = 0.0d0

    do j = 1, n
      v = a(:, j)
      do i = 1, j - 1
        r(i, j) = dot_product(q(:, i), a(:, j))
        v = v - r(i, j) * q(:, i)
      end do
      norm_v = sqrt(max(dot_product(v, v), 1.0d-12))
      r(j, j) = norm_v
      q(:, j) = v / norm_v
    end do
  end subroutine qr_decompose

  function simpson_integrate(y, h, n) result(integral)
    integer, intent(in) :: n
    real(8), intent(in) :: y(n), h
    real(8) :: integral
    integer :: i

    integral = y(1) + y(n)
    do i = 2, n - 1
      if (mod(i, 2) == 0) then
        integral = integral + 4.0d0 * y(i)
      else
        integral = integral + 2.0d0 * y(i)
      end if
    end do
    integral = integral * h / 3.0d0
  end function simpson_integrate

  function gauss_legendre_integrate(a, b) result(integral)
    real(8), intent(in) :: a, b
    real(8) :: integral
    real(8) :: x1, x2, midpoint, half_width

    midpoint = (a + b) / 2.0d0
    half_width = (b - a) / 2.0d0
    x1 = midpoint - half_width / sqrt(3.0d0)
    x2 = midpoint + half_width / sqrt(3.0d0)
    integral = half_width * (integrand(x1) + integrand(x2))
  end function gauss_legendre_integrate

  subroutine rk4_step(y, t, h, y_next)
    real(8), intent(in) :: y, t, h
    real(8), intent(out) :: y_next
    real(8) :: k1, k2, k3, k4

    k1 = h * ode_rhs(t, y)
    k2 = h * ode_rhs(t + 0.5d0 * h, y + 0.5d0 * k1)
    k3 = h * ode_rhs(t + 0.5d0 * h, y + 0.5d0 * k2)
    k4 = h * ode_rhs(t + h, y + k3)
    y_next = y + (k1 + 2.0d0 * k2 + 2.0d0 * k3 + k4) / 6.0d0
  end subroutine rk4_step

  function newton_raphson(initial_guess, tolerance, max_iter) result(root)
    real(8), intent(in) :: initial_guess, tolerance
    integer, intent(in) :: max_iter
    real(8) :: root
    integer :: i

    root = initial_guess
    do i = 1, max_iter
      root = root - function_value(root) / function_derivative(root)
      if (abs(function_value(root)) < tolerance) exit
    end do
  end function newton_raphson

  function bisection(lower, upper, tolerance, max_iter) result(root)
    real(8), intent(in) :: lower, upper, tolerance
    integer, intent(in) :: max_iter
    real(8) :: root, left, right, midpoint
    integer :: i

    left = lower
    right = upper
    midpoint = (left + right) / 2.0d0

    do i = 1, max_iter
      midpoint = (left + right) / 2.0d0
      if (abs(function_value(midpoint)) < tolerance) exit
      if (function_value(left) * function_value(midpoint) < 0.0d0) then
        right = midpoint
      else
        left = midpoint
      end if
    end do

    root = midpoint
  end function bisection

  real(8) function ode_rhs(t, y)
    real(8), intent(in) :: t, y
    ode_rhs = -0.5d0 * y + sin(t)
  end function ode_rhs

  real(8) function function_value(x)
    real(8), intent(in) :: x
    function_value = x * x - 2.0d0
  end function function_value

  real(8) function function_derivative(x)
    real(8), intent(in) :: x
    function_derivative = 2.0d0 * x
  end function function_derivative

  real(8) function integrand(x)
    real(8), intent(in) :: x
    integrand = exp(-x * x)
  end function integrand

end module math_lib
