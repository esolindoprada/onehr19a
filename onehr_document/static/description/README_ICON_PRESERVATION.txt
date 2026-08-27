The uploaded historical onehr_document scaffold may contain a binary icon in the
user workspace that is not represented in the text dump. This Direct Full Build
does not fabricate a replacement binary. `deploy_to_workspace.ps1` preserves and
restores the existing static/description/icon.png when one exists.
