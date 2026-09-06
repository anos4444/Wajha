"""Second pass for sites where remove_swift_theme already ran before it
dropped tables: the two child tables (`tabSwift Theme Sound Event`,
`tabSwift Home Card`) survived the DocType deletion on the hub."""

from wajha.patches.remove_swift_theme import drop_tables


def execute():
    drop_tables()
