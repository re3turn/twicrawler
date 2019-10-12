#!/usr/bin/python3

from app import google_photos


def main() -> None:
    google_photos.GooglePhotos.get_access_token()


if __name__ == '__main__':
    main()
