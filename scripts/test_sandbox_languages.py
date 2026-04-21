from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from HomeworkModule.sandbox_service import SandboxService


def main() -> None:
    service = SandboxService()
    cases = [{"input": "2 3\n", "expected": "5", "weight": 100, "is_file_io": False}]

    py_code = "a, b = map(int, input().split())\nprint(a + b)\n"
    cpp_code = """
#include <bits/stdc++.h>
using namespace std;
int main() {
    long long a, b;
    if (!(cin >> a >> b)) return 0;
    cout << (a + b) << "\\n";
    return 0;
}
""".strip()
    java_code = """
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        long a = sc.nextLong();
        long b = sc.nextLong();
        System.out.println(a + b);
    }
}
""".strip()

    for lang, code in (("python", py_code), ("cpp", cpp_code), ("java", java_code)):
        report = service.judge_code(code=code, language=lang, test_cases=cases)
        detail = report.get("details", [{}])[0]
        print(f"{lang}: status={detail.get('status')} ok={detail.get('ok')} stdout={detail.get('actual')!r} stderr={detail.get('stderr')!r}")


if __name__ == "__main__":
    main()
