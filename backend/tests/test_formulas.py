from decimal import Decimal


def earned_salary(monthly_salary: int, divisor: int, attendance_units: Decimal) -> int:
    return int(Decimal(monthly_salary) / divisor * attendance_units)


def distributable_profit(
    income: int, project_expenses: int, general_expenses: int, payroll: int
) -> int:
    return income - project_expenses - general_expenses - payroll


def test_earned_salary_uses_attendance_units() -> None:
    assert earned_salary(6_000_000, 30, Decimal("20")) == 4_000_000
    assert earned_salary(6_000_000, 30, Decimal("19.5")) == 3_900_000


def test_profit_can_be_a_loss() -> None:
    assert distributable_profit(1_000_000, 400_000, 300_000, 500_000) == -200_000
