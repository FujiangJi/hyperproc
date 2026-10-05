# hyperproc.archive.dlr._Forms

Release baseline **0.1.2**. Fields and declared members below come from the release source. Dataclass/inherited methods may be generated at runtime; inspect the installed class signature when constructing it.

Every form on a sign-on page, kept **apart**.

Keeping them apart is the whole point. DLR's EnMAP sign-on carries two: the
EOC username/password form, and a hidden one whose only job is to hand you
off to the EO-Lab identity provider. Merging their fields - as an earlier
version did - meant posting the delegation form's ``_eventId`` along with
the credentials, so the sign-on obligingly redirected to EO-Lab's Keycloak
and the EOC password was never tried. DESIS's page has one form, which is
why it worked there and not here.

## Declared members

- [__init__](hyperproc.archive.dlr._Forms.__init__.md)
- [handle_starttag](hyperproc.archive.dlr._Forms.handle_starttag.md)
- [handle_endtag](hyperproc.archive.dlr._Forms.handle_endtag.md)
- [handle_data](hyperproc.archive.dlr._Forms.handle_data.md)
- [login](hyperproc.archive.dlr._Forms.login.md)
- [step](hyperproc.archive.dlr._Forms.step.md)
- [fields](hyperproc.archive.dlr._Forms.fields.md)

[Module](../hyperproc-archive-dlr.md).
