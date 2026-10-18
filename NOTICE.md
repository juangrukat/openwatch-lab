# Notices and provenance

OpenWatch Lab application code is licensed under AGPL-3.0-or-later. Original protocol documentation and fabricated fixtures are dedicated under CC0-1.0. These documents describe observed compatibility behavior, not ownership of a vendor protocol.

Gadgetbridge's Moyoung implementation was consulted as reference material, alongside local shipped-app inspection and watch experiments. Gadgetbridge is AGPL-3.0-or-later: https://codeberg.org/Freeyourgadget/Gadgetbridge . Reference files consulted on 2026-10-18 include MoyoungPacketOut.java, FetchDataOperation.java, MoyoungConstants.java, MoyoungDeviceSupport.java and FetchWorkoutsV2Operation.java. No vendor binary or personal traffic capture is distributed here.

Electron and Chromium notices accompany the packaged Electron runtime. React, React DOM, Lucide and all Python dependencies retain their own licenses. The backend bundler copies available installed distribution license files into THIRD-PARTY-NOTICES.txt beside its executable. Source dependencies and exact JavaScript versions are recorded in pyproject.toml and package-lock.json; rebuild with those tools and review notices before redistribution.
