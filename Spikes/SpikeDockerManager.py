"""Console spike to interactively exercise DockerManager functionality."""

MENU_OPTIONS = {
    "1": "Ensure image is available",
    "2": "Start PostgreSQL container",
    "3": "Create temporary database",
    "4": "Remove temporary database",
    "5": "Show connection parameters",
    "6": "Stop container",
    "7": "Remove container",
    "8": "Reload configuration",
    "9": "Exit",
}


def display_menu() -> None:
    """Print the available spike actions."""
    print("\nSpike Docker Manager UI")
    for key, description in MENU_OPTIONS.items():
        print(f"  {key}. {description}")


def prompt_temp_db(known_dbs: list[str]) -> str | None:
    """Prompt user to select a temporary database name from known values."""
    if not known_dbs:
        print("No temporary databases recorded in this session.")
        return None

    print("Known temporary databases:")
    for index, name in enumerate(known_dbs, start=1):
        print(f"  {index}. {name}")

    selection = input("Select database by number (or press Enter to cancel): ").strip()
    if not selection:
        return None

    try:
        selected_index = int(selection)
    except ValueError:
        print("Invalid selection; please enter a number.")
        return None

    if 1 <= selected_index <= len(known_dbs):
        return known_dbs[selected_index - 1]

    print("Selection outside valid range.")
    return None


def main() -> None:
    """Run a simple loop for exercising DockerManager operations."""
    import logging
    import sys
    from pathlib import Path

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from models.docker_manager import DockerManager

    manager = DockerManager()
    temp_databases: list[str] = []

    while True:
        display_menu()
        choice = input("Choose an option: ").strip()

        if choice == "1":
            try:
                manager.ensure_image()
                print("Image validation complete.")
            except Exception as exc:  # pragma: no cover - spike diagnostic output
                print(f"Failed to ensure image: {exc}")
        elif choice == "2":
            name = input("Container name [test_postgres]: ").strip() or "test_postgres"
            port_text = input("Host port [5432]: ").strip() or "5432"
            user = input("Postgres user [testuser]: ").strip() or "testuser"
            password = input("Postgres password [testpass]: ").strip() or "testpass"
            database = input("Postgres database [testdb]: ").strip() or "testdb"
            image_input = input("Image override (leave blank for configured value): ").strip()
            image_override = image_input or None

            try:
                port_value = int(port_text)
            except ValueError:
                print("Invalid port; using 5432.")
                port_value = 5432

            try:
                params = manager.start_postgres_container(
                    container_name=name,
                    postgres_user=user,
                    postgres_password=password,
                    postgres_db=database,
                    port=port_value,
                    image_tag=image_override,
                )
                print("Container started with parameters:")
                for key, value in params.items():
                    print(f"  {key}: {value}")
            except Exception as exc:  # pragma: no cover - spike diagnostic output
                print(f"Failed to start container: {exc}")
        elif choice == "3":
            try:
                db_name = manager.add_tmp_db()
                temp_databases.append(db_name)
                print(f"Temporary database created: {db_name}")
            except Exception as exc:  # pragma: no cover - spike diagnostic output
                print(f"Failed to create temporary database: {exc}")
        elif choice == "4":
            selected_db = prompt_temp_db(temp_databases)
            if selected_db:
                try:
                    manager.remove_tmp_db(selected_db)
                    temp_databases = [db for db in temp_databases if db != selected_db]
                    print(f"Temporary database removed: {selected_db}")
                except Exception as exc:  # pragma: no cover - spike diagnostic output
                    print(f"Failed to remove temporary database: {exc}")
        elif choice == "5":
            params = manager.get_connection_params()
            if params:
                print("Current connection parameters:")
                for key, value in params.items():
                    print(f"  {key}: {value}")
            else:
                print("No active connection parameters recorded.")
        elif choice == "6":
            try:
                manager.stop_container()
                print("Stop signal issued to container.")
            except Exception as exc:  # pragma: no cover - spike diagnostic output
                print(f"Failed to stop container: {exc}")
        elif choice == "7":
            try:
                manager.remove_container()
                print("Container removal attempted.")
            except Exception as exc:  # pragma: no cover - spike diagnostic output
                print(f"Failed to remove container: {exc}")
        elif choice == "8":
            manager.reload_configuration()
            print(f"Configuration reloaded. Active image tag: {manager.image_tag}")
        elif choice == "9":
            manager.cleanup()
            print("Cleanup complete. Exiting.")
            break
        else:
            print("Unrecognized option. Please choose again.")


if __name__ == "__main__":
    main()
