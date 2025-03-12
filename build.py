#!/usr/bin/env python3
import subprocess


class LocalBuilder:

    def get_new_version(self) -> str:
        """Get the new version using semantic-release."""
        # Run version to update version files and create git tag
        subprocess.run(
            ["semantic-release", "version", "--no-changelog", "--no-vcs-release"],
            check=True,
        )

        # Get the current version
        result = subprocess.run(
            ["semantic-release", "version", "--print"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def run(self):
        """Main execution method."""
        try:
            # Get new version using semantic-release
            version = self.get_new_version()
            print(f"New version determined by semantic-release: {version}")

        except subprocess.CalledProcessError as e:
            print(f"Error during build process: {e}")
            raise
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise


if __name__ == "__main__":
    LocalBuilder().run()
