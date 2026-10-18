# Anti-cheat compatibility testing (BT, GhostX, Global, others)

Compatibility is **unverified** until you record evidence. The profiles in `compat_profiles/` are checklists, not claims.
They were written without assuming any undocumented behavior of any product.

## Rules
- Test only on a server you own or have written permission to test, and with the anti-cheat vendor's terms in mind.
- Do not try to hide this resource from, or defeat, any anti-cheat. If a product flags the resource, record that and
  contact the vendor to allow-list it, or leave it out of that server.
- No product can be promised to leave you unflagged. This project makes no such promise.

## Procedure
1. Open **Security > Compatibility** and pick a product.
2. Work through each check on your test server.
3. Record the result (pass, partial, fail), the product version and server build, and what you saw.
4. The result is stored in your config and appears as that product's status. The default stays `untested`.

To add a product, copy `compat_profiles/other.json`, change `id` and `name`, and add checks from that product's own documentation.
