#!/usr/bin/env python3
import subprocess

class LocalBuilder:
    def __init__(self):
        self.docker_image_name = "cashio-api"

    def get_current_git_hash(self) -> str:
        """Get the current git commit hash."""
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()

    def get_new_version(self) -> str:
        """Get the new version using semantic-release."""
        # Run version to update version files and create git tag
        subprocess.run(["semantic-release", "version", "--no-changelog", "--no-push"], check=True)
        
        # Get the current version
        result = subprocess.run(
            ["semantic-release", "version", "--print"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()

    def build_docker_image(self, version: str):
        """Build Docker image with version tag."""
        
        # Create tags for the image
        version_tag = f"{self.docker_image_name}:{version}"
        latest_tag = f"{self.docker_image_name}:latest"
        
        # Build the Docker image
        print(f"Building Docker image with tags: {version_tag}, {latest_tag}")
        subprocess.run([
            "docker", "build",
            "-t", version_tag,
            "-t", latest_tag,
            "."
        ], check=True)
        
        return version_tag, latest_tag

    def run(self):
        """Main execution method."""
        try:
            # Get new version using semantic-release
            version = self.get_new_version()
            print(f"New version determined by semantic-release: {version}")
            
            # Build Docker image
            version_tag, latest_tag = self.build_docker_image(version)
            print("\nSuccessfully built Docker images with tags:")
            print(f"- {version_tag}")
            print(f"- {latest_tag}")
            
        except subprocess.CalledProcessError as e:
            print(f"Error during build process: {e}")
            raise
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise

if __name__ == "__main__":
    builder = LocalBuilder().run()
