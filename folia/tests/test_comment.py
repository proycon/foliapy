#!/usr/bin/env python3
import unittest
import folia.main as folia


def test_parse_comments():
    folia.Document(
        string="""<?xml version="1.0" encoding="utf-8"?>
<?xml-stylesheet type="text/xsl" href="folia.xsl"?>
<!-- Foo -->
<FoLiA xmlns="http://ilk.uvt.nl/folia" version="2.0" xml:id="example">
  <!-- Foo -->
  <text>
    <!-- Foo -->
    <p>
      <!-- Foo -->
      <t><!-- Foo -->Dit is een test.</t>
    <!-- Foo -->
    </p>
    <!-- Foo -->
  </text>
  <!-- Foo -->
</FoLiA>
<!-- Foo -->
""",
        autodeclare=True,
        loadsetdefinitions=False,
    )
