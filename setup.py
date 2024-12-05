from setuptools import setup, find_packages

setup(
    name="slurm-job-tracker",
    version="1.0.0",
    author="Ivan Tambovtsev",
    author_email="your_email@example.com",
    description="A tool for tracking and managing Slurm jobs with an HTTP server",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/your_github_username/slurm-job-tracker",  # Replace with the actual repo URL
    packages=find_packages(),
    include_package_data=True,  # Ensures JSON files are included
    install_requires=[
        "requests",  # Add other dependencies here
    ],
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "slurm-job-tracker=slurm_job_tracker.main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
