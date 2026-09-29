#!/usr/bin/env bash
# Run inside the built Live rootfs or a booted GallosOS session.
set -euo pipefail

for program in gcc g++ clang++ javac java python3 pypy3 rustc kotlinc \
    geany firefox codium squid; do
    command -v "$program" >/dev/null || {
        echo "Missing release program: $program" >&2
        exit 1
    }
done

scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
cd "$scratch"

cat > main.c <<'EOF'
#include <stdio.h>
int main(void) { puts("42"); return 0; }
EOF
gcc main.c -o c-program
[[ "$(./c-program)" == "42" ]]

cat > main.cpp <<'EOF'
#include <iostream>
int main() { std::cout << 42 << '\n'; }
EOF
g++ main.cpp -o cpp-program
clang++ main.cpp -o clang-program
[[ "$(./cpp-program)" == "42" ]]
[[ "$(./clang-program)" == "42" ]]

cat > Main.java <<'EOF'
public class Main { public static void main(String[] args) { System.out.println(42); } }
EOF
javac Main.java
[[ "$(java Main)" == "42" ]]

[[ "$(python3 -c 'print(42)')" == "42" ]]
[[ "$(pypy3 -c 'print(42)')" == "42" ]]

cat > main.rs <<'EOF'
fn main() { println!("42"); }
EOF
rustc main.rs -o rust-program
[[ "$(./rust-program)" == "42" ]]

cat > Main.kt <<'EOF'
fun main() { println(42) }
EOF
kotlinc Main.kt -include-runtime -d main.jar
[[ "$(java -jar main.jar)" == "42" ]]

echo "All advertised language families compiled or ran successfully."
