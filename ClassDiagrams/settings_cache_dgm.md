# Settings Cache - UML Class Diagram

```mermaid
classDiagram
    class SettingCache {
        +Dict[Tuple[str, str], SettingCacheEntry] entries
        +Dict[str, SettingType] setting_types
        +__init__()
        +get(setting_type_id, related_entity_id) Optional[SettingCacheEntry]
        +set(setting_type_id, related_entity_id, entry)
        +remove(setting_type_id, related_entity_id) bool
        +get_setting_type(setting_type_id) Optional[SettingType]
        +set_setting_type(setting_type_id, setting_type)
        +clear()
        +get_dirty_entries() List[SettingCacheEntry]
        +get_deleted_entries() List[SettingCacheEntry]
    }

    class SettingCacheEntry {
        +Setting setting
        +bool is_dirty
        +bool is_deleted
        +__init__(setting)
        +mark_dirty()
        +mark_clean()
        +mark_deleted()
        +is_new() bool
    }

    SettingCache "1" *-- "many" SettingCacheEntry : contains
    SettingCache "1" *-- "many" SettingType : contains
    SettingCacheEntry --> Setting : wraps

    note for SettingCache "In-memory cache for settings and setting types\nwith dirty flag tracking for efficient persistence"
    note for SettingCacheEntry "Cache entry wrapper with state tracking\nfor optimized database operations"
```
