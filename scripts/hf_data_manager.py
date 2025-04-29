import os
from pathlib import Path
from huggingface_hub import HfApi, Repository, login, create_repo
import argparse
from dotenv import load_dotenv

def load_env_vars():
    load_dotenv()
    hf_username = os.getenv("HF_USERNAME")
    hf_token = os.getenv("HF_TOKEN")
    
    if not hf_username or not hf_token:
        raise ValueError("HF_USERNAME and HF_TOKEN must be set in .env file")
    
    return hf_username, hf_token

def ensure_repo_exists(repo_id):
    api = HfApi()
    try:
        api.repo_info(repo_id=repo_id, repo_type="dataset")
    except:
        print(f"Repository {repo_id} not found. Creating it...")
        create_repo(
            repo_id=repo_id,
            repo_type="dataset",
            exist_ok=True
        )
        print(f"Repository {repo_id} created successfully!")

def upload_to_hf(repo_id, data_dir="data"):
    api = HfApi()
    
    print(f"Uploading files from {data_dir} to {repo_id}...")
    
    for file in Path(data_dir).glob("*"):
        if file.is_file():
            print(f"Uploading {file.name}...")
            api.upload_file(
                path_or_fileobj=str(file),
                path_in_repo=file.name,
                repo_id=repo_id,
                repo_type="dataset"
            )
    print("Upload completed!")

def upload_dataset_card(repo_id):
    api = HfApi()
    print("Uploading dataset card...")
    api.upload_file(
        path_or_fileobj="dataset_card.md",
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="dataset"
    )
    print("Dataset card uploaded successfully!")

def download_from_hf(repo_id, data_dir="data"):
    api = HfApi()
    
    print(f"Downloading files from {repo_id} to {data_dir}...")
    
    os.makedirs(data_dir, exist_ok=True)
    
    files = api.list_repo_files(repo_id, repo_type="dataset")
    for file in files:
        if file != ".gitattributes":
            print(f"Downloading {file}...")
            api.hf_hub_download(
                repo_id=repo_id,
                filename=file,
                repo_type="dataset",
                local_dir=data_dir
            )
    print("Download completed!")

def main():
    parser = argparse.ArgumentParser(description="Manage data uploads and downloads with Hugging Face")
    parser.add_argument("--repo-id", required=True, help="Hugging Face repository ID")
    parser.add_argument("--action", choices=["upload", "download", "upload-card"], required=True, help="Action to perform")
    parser.add_argument("--data-dir", default="data", help="Directory containing data files")
    
    args = parser.parse_args()
    
    hf_username, hf_token = load_env_vars()
    login(token=hf_token)
    
    if args.action == "upload":
        ensure_repo_exists(args.repo_id)
        upload_to_hf(args.repo_id, args.data_dir)
    elif args.action == "upload-card":
        ensure_repo_exists(args.repo_id)
        upload_dataset_card(args.repo_id)
    else:
        download_from_hf(args.repo_id, args.data_dir)

if __name__ == "__main__":
    main() 