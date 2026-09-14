## 0.7.1 — Fix HACS README image and add installation button

The README logo now uses an absolute public image URL so it can load outside
GitHub, including the HACS repository description. The installation section adds
the official blue **Open HACS Repository** badge, linking directly to this custom
integration with its owner, repository and category filled in.

HACS normally reads documentation from the installed version. Update to **0.7.1**
to receive the corrected description, then reopen the repository page.

The supervised temperature experiment from 0.7.0 is unchanged. Installation and
restart still send nothing; preparation and sending remain separate admin actions.
No live write test was performed as part of this release.

Update through HACS and restart Home Assistant. Follow the
[German test guide](https://github.com/DNier/proxon-hesp-homeassistant/blob/v0.7.1/docs/SOLLTEMPERATUR_TEST.md)
when ready to start the experiment.

Validation: logo and badge endpoints returned HTTP 200 with the expected image
content types; the repository link follows the official HACS My-link format.
The preceding README commit passed all 180 tests and HACS validation. The release
workflow runs the same test suite again before publication.
