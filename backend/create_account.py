"""
Creates an owner account from the command line, optionally starting from an
existing database (e.g. your current menu.db from before logins existed).

    cd backend
    .\\venv\\Scripts\\python.exe create_account.py you@example.com --from-db menu.db

It asks for the password (typed twice, not shown). Without --from-db the
account starts with the benchmark ingredients only, like signing up in the app.
"""

import argparse
import getpass
import shutil
import sys

import auth
from seed_demo import reset_database


def main():
    parser = argparse.ArgumentParser(description='Create an owner account.')
    parser.add_argument('email')
    parser.add_argument('--from-db', help='copy this database into the new account (e.g. menu.db)')
    args = parser.parse_args()

    email = args.email.strip().lower()
    auth.init_auth()
    with auth.AuthSession() as session:
        if session.query(auth.Account).filter(auth.Account.email == email).first():
            sys.exit(f'There is already an account for {email}.')

    password = getpass.getpass('Password (8+ characters): ')
    if len(password) < auth.MIN_PASSWORD:
        sys.exit('The password must be at least 8 characters.')
    if getpass.getpass('Password again: ') != password:
        sys.exit("The passwords don't match.")

    with auth.AuthSession() as session:
        account = auth.Account(email=email, password_hash=auth.hash_password(password), kind='owner')
        session.add(account)
        session.commit()

    if args.from_db:
        folder = auth.account_folder(account.id)
        shutil.copy(args.from_db, folder / 'menu.db')
        if (auth.BACKEND / 'uploads').exists():   # the files its imports were read from
            shutil.copytree(auth.BACKEND / 'uploads', folder / 'uploads', dirs_exist_ok=True)
        auth.engine_for(account.id)   # adds any tables the old database doesn't have yet
        print(f'Created {email} (account {account.id}) with the data from {args.from_db}.')
    else:
        reset_database(auth.engine_for(account.id), with_demo=False)
        print(f'Created {email} (account {account.id}), starting with the benchmark ingredients.')


if __name__ == '__main__':
    main()
