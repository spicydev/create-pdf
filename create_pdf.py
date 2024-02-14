#!/usr/bin/env python
"""
Python Utility to create searchable pdf from series of images downloaded using specific format.
Images must be provided in a specified format containing base-url, subject name and chapters prefix.
"""
import argparse
import os
from concurrent.futures import ThreadPoolExecutor
import pytesseract
import requests
from PIL import Image


def create_pdf(base_url: str, subject: str, chapter_prefix: str) -> None:
    """Creates a new searchable pdf by downloading images.
        Ex: base_url = https://www.example.com/, subject: SUB, chapter_prefix: A
        so final url for downloading images is - https://www.example.com/SUB/A1/001.jpg.
        Supports Total 19 chapters like A1 to A19 and pages from 1 to 999.
    """
    download_chapters(base_url+subject+'/', subject, chapter_prefix)
    generate_pdf(subject)

def download_chapters(url: str, subject: str, chapter_prefix: str) -> None:
    """Downloads Images from Chapters using the url, subject and chapter prefix."""
    for i in range(1,20):
        chapter = chapter_prefix + f'{i}'
        print('Downloading Chapter ' + chapter)
        result = download_chapter(url+chapter+'/', subject, chapter)
        if result == True:
            print('Finished Downloading Chapter '+ chapter)

def download_chapter(url: str, subject: str, chapter: str) -> bool:
    """Downloads Images from Chapter using the url, subject and chapter name."""
    n_cores = min(32, os.cpu_count() or 4 + 4)
    with ThreadPoolExecutor(max_workers=n_cores) as executor:
        for i in range(1,1000, n_cores):
            params=[]
            for j in range(i, i-n_cores, -1):
                if j > 0:
                    image = f'{j:>03}'+'.jpg'
                    params.append((url+image, image, subject, chapter))
            results = list(executor.map(download_img_helper, params))
            params=[]
            if False in results:
                return True

    return False


def download_img_helper(params: tuple) -> bool:
    """Helper Function to download image using tuple as input."""
    return download_image(params[0], params[1], params[2], params[3])

def download_image(url: str, image: str, subject: str, chapter: str) -> bool:
    """Downloads image using url, subject, chapter and image names."""
    try:
        resp = requests.get(url, timeout=2, stream=True)
        if resp.status_code == 200:
            img = Image.open(resp.raw)
            path = os.path.join(subject, chapter)
            if not os.path.exists(path):
                os.makedirs(path)
            path = os.path.join(path, image)
            img.save(path)
            print('Downloaded Image '+image)
            with open(subject+'-pages.txt', mode='a', encoding='utf-8') as file:
                file.write(path)
                file.write('\n')
            return True
        else:
            print('Failed Downloading Image '+image+', Response: '+resp.reason)
            return False
    except Exception as err:
        print('Failed Downloading Image '+image, err)
        return False

def generate_pdf(subject: str) -> None:
    """Generate searchable pdf using teserract from sorted images."""
    with open(subject+'-pages.txt', encoding='utf-8') as in_file:
        with open(subject+'-sorted-pages.txt', mode='w', encoding='utf-8') as out_file:
            out_file.write('\n'.join(sorted(in_file.read().splitlines())))
    print('Generating pdf output..')
    pdf = pytesseract.image_to_pdf_or_hocr(subject+'-sorted-pages.txt', extension='pdf')
    with open(subject+'.pdf', mode='w+b', encoding='utf-8') as out_file:
        out_file.write(pdf)
        out_file.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")
    create_parser = subparsers.add_parser("create", help=create_pdf.__doc__)
    create_parser.add_argument("base_url")
    create_parser.add_argument("subject")
    create_parser.add_argument("chapter_prefix")

    args = create_parser.parse_args()

    if args.command == "create":
        create_pdf(args.base_url, args.subject, args.chapter_prefix)
