# make_ingest.py

import sys
import subprocess


def generate_digest_cli(source, output_file="digest.txt", exclude_exts=None):
    cmd = ["gitingest", source, "-o", output_file]

    # Comprehensive exclusions for common non-essential files and directories
    exclusions = [
        # Project-specific directories
        "ai_ap_manager",
        "ai_ap_manager/*",
        "invoices",
        "processed_documents",
        "sample_data",
        "README.md",
        # Python-related
        "__pycache__",
        "__pycache__/*",
        "*/__pycache__",
        "*/__pycache__/*",
        "**/__pycache__/**",
        "*.pyc",
        "*.pyo",
        "*.egg-info",
        ".pytest_cache",
        "venv",
        "venv/*",
        ".venv",
        "env",
        ".env",
        "reference/*",
        # Poetry and dependency management
        "poetry.lock",
        "*/poetry.lock",
        "ai_ap_manager/*/poetry.lock",
        # Database and vector store files (ai_ap_manager specific)
        "chroma_db",
        "chroma_db/*",
        "*/chroma_db",
        "*/chroma_db/*",
        "**/chroma_db/**",
        "ai_ap_manager/*/chroma_db",
        "ai_ap_manager/*/chroma_db/*",
        "*.sqlite3",
        "*.sqlite",
        "*.db",
        "chroma.sqlite3",
        # Binary data files (vector store related)
        "*.bin",
        "data_level0.bin",
        "ai_ap_manager/",
        "ai_ap_manager/*",
        "header.bin",
        "length.bin",
        "link_lists.bin",
        # Version control
        ".git",
        ".gitignore",
        # System files
        ".DS_Store",
        "Thumbs.db",
        "desktop.ini",
        # Build and distribution
        "build",
        "dist",
        "*.egg",
        # Logs and temporary files
        "*.log",
        "*.tmp",
        "*.temp",
        "logs",
        # Documentation and media files
        "*.pdf",
        "*.doc",
        "*.docx",
        "*.xls",
        "*.xlsx",
        "*.ppt",
        "*.pptx",
        "*.png",
        "*.jpg",
        "*.jpeg",
        "*.gif",
        "DOCKER_GUIDE.md",
        "*.svg",
        "*.ico",
        # IDE and editor files
        ".vscode",
        ".idea",
        "*.swp",
        "*.swo",
        "database_export",
        "database_export/*",
        # Node.js and React/Next.js related - more comprehensive exclusions
        "node_modules",
        "node_modules/*",
        "*/node_modules",
        "*/node_modules/*",
        "**/node_modules/**",
        "supervity-ap-frontend/node_modules",
        "supervity-ap-frontend/node_modules/*",
        "supervity-ap-frontend/package-lock.json",
        "supervity-ap-frontend/yarn.lock",
        "supervity-ap-frontend/pnpm-lock.yaml",
        "supervity-ap-frontend/.next",
        "supervity-ap-frontend/.next/*",
        "supervity-ap-frontend/public",
        "supervity-ap-frontend/public/*",
        "supervity-ap-frontend/.nuxt",
        "supervity-ap-frontend/.nuxt/*",
        "supervity-ap-frontend/out",
        "supervity-ap-frontend/out/*",
        "supervity-ap-frontend/build",
        "supervity-ap-frontend/dist",
        "supervity-ap-frontend/.cache",
        "supervity-ap-frontend/.parcel-cache",
        "supervity-ap-frontend/.vercel",
        "supervity-ap-frontend/.netlify",
        "supervity-ap-frontend/coverage",
        "supervity-ap-frontend/.nyc_output",
        "supervity-ap-frontend/.storybook-build",
        "supervity-ap-frontend/storybook-static",
        "supervity-ap-frontend/.turbo",
        "supervity-ap-frontend/.swc",
        "supervity-ap-frontend/.tsbuildinfo",
        "supervity-ap-frontend/*.tsbuildinfo",
        "npm-debug.log",
        "yarn-error.log",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        ".next",
        ".next/*",
        ".nuxt",
        ".nuxt/*",
        "out",
        "out/*",
        "build",
        "dist",
        ".cache",
        ".parcel-cache",
        ".vercel",
        ".netlify",
        "coverage",
        ".nyc_output",
        ".storybook-build",
        "storybook-static",
        ".turbo",
        ".swc",
        ".tsbuildinfo",
        "*.tsbuildinfo",
        # Archives
        "*.zip",
        "*.tar",
        "*.tar.gz",
        "*.rar",
        "*.7z",
    ]

    if exclude_exts:
        # Format extensions as "*.ext" and add to exclusions
        exclusions.extend(f"*{ext}" for ext in exclude_exts)

    if exclusions:
        patterns = ",".join(exclusions)
        cmd += ["-e", patterns]

    print("Running:", " ".join(cmd))

    try:
        subprocess.run(cmd, check=True)
        print(f"✅ Digest written to {output_file}")
    except subprocess.CalledProcessError as e:
        print("❌ Error during gitingest execution:", e)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python make_ingest.py <path_or_url> [output_file] [excluded_exts...]"
        )
        sys.exit(1)

    source = sys.argv[1]

    # Determine if second argument is an output file or an extension
    output_file = "digest.txt"
    exclude_exts = []

    if len(sys.argv) >= 3 and sys.argv[2].startswith(".") is False:
        output_file = sys.argv[2]
        exclude_exts = sys.argv[3:]
    else:
        exclude_exts = sys.argv[2:]

    generate_digest_cli(source, output_file, exclude_exts)
