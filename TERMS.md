# SmartAttend Terms of Use

**Status: draft, not legal advice.** Like [PRIVACY.md](PRIVACY.md), this was drafted from the actual behavior of the SmartAttend codebase and needs review by your institution before it governs real students, lecturers, or administrators.

*Last drafted: 2026-09-04.*

## 1. What this covers

These terms govern use of the SmartAttend web application by students, lecturers, and administrators at **[Institution name — fill in]**. By signing in, you agree to them. If you're a student using self-registration, agreeing to these terms and to biometric data collection (see [PRIVACY.md](PRIVACY.md)) is a condition of getting an account.

## 2. What SmartAttend does

SmartAttend records classroom attendance using two checks that must both pass: scanning a short-lived, cryptographically signed QR code the lecturer displays in the room, and a live face verification against the photo you provided at enrollment. Both are required — one without the other does not mark you present. This exists to prevent one student checking in on behalf of another ("proxy attendance"), not to monitor you outside the moment you check in.

## 3. Accounts and eligibility

- **Students** may either be enrolled directly by an administrator/lecturer, or self-register through the registration form — self-registration accounts sit in a pending state until an administrator reviews and approves them; approval is not automatic or guaranteed.
- **Lecturers and administrators** are provisioned by the institution, not through self-registration.
- You're responsible for keeping your password confidential and for activity on your account. If you believe your account has been compromised, tell an administrator so your sessions can be revoked.
- You must provide accurate name, matric number, department, and level information. Providing false identity information to obtain or use an account is a violation of these terms and, for a student proxying attendance for someone else, likely a violation of your institution's own academic integrity policy separately from anything in this document.

## 4. Biometric consent

Enrolling your face for verification is a distinct, explicit action, not a side effect of creating an account — the self-registration flow records your consent to biometric processing at the point you provide it. See [PRIVACY.md](PRIVACY.md) §2.2 for exactly what is and isn't done with that data (short version: your photo is processed in memory and discarded; only a mathematical representation of it is stored, and it is used solely to verify your identity at check-in).

You may decline or withdraw biometric consent. Doing so means you cannot use the automatic face-verification check-in, and your institution's fallback manual attendance process (outside this system) applies instead — declining does not entitle you to a face-verification-free path through this system, since face verification is one of the two required checks.

## 5. Acceptable use

You agree not to:
- Attempt to check in on behalf of another student, or ask/allow someone else to check in on your behalf.
- Attempt to circumvent, spoof, or replay the face-verification or QR check — including presenting a photo or recording instead of your live face, or submitting a captured frame more than once.
- Share your account credentials or session tokens with anyone else.
- Attempt to access another user's data, another lecturer's course records, or administrative functions you haven't been granted.
- Probe, load-test, or attempt to disrupt the system outside of authorized testing.

Violations may result in account suspension and, for students, referral to your institution's academic integrity process — SmartAttend enforces the technical checks, but the consequences for defeating them are your institution's to decide, not this document's.

## 6. Lecturer and administrator responsibilities

If you hold a lecturer or admin role, you additionally agree to:
- Only display QR check-in codes to students actually present in your class session — the QR mechanism assumes good faith on the display side; it has no way to independently confirm the projector is pointed at a real classroom.
- Review flagged/failed attendance attempts fairly, since a genuine student can be wrongly rejected by the face-match (lighting, camera quality, and comparable technical factors can cause false rejections) — the system separates flagged attempts from confirmed ones specifically so a human reviews the edge cases rather than the system silently penalizing them.
- Review pending student self-registrations in good faith and within a reasonable time, since a pending student cannot check into attendance until approved.
- Not use administrative or lecturer access to view students' data for any purpose outside operating the course.

## 7. Availability and accuracy

SmartAttend is provided as-is. We do not guarantee the service will be available at every moment a class meets, and technical failures (camera issues, network conditions, model false negatives/positives) can occur. Where the automated check fails a genuine student, the flagged-attempt review process (§6) exists precisely to correct that — it is not a promise that the automated check will never make a mistake. Your institution is responsible for defining what backup attendance process applies if SmartAttend is unavailable during a class.

## 8. Changes to the service and these terms

Because this is an actively developed academic project, features, the verification pipeline, and these terms may change. Material changes to what data is collected or how biometric verification works will be reflected in an updated [PRIVACY.md](PRIVACY.md) with a new date; continued use after a change means you've had the opportunity to review it.

## 9. Account termination

An administrator may suspend or remove an account for a violation of §5, at the end of your enrollment/employment at the institution, or as required by institutional policy. You may request account deletion; see [PRIVACY.md](PRIVACY.md) §5 and §6 for the current limitations on data deletion — as implemented today, deletion is a manual administrative action, not a self-service one.

## 10. Governing framework

These terms operate alongside your institution's own academic and data-protection policies and applicable Nigerian law, including the Nigeria Data Protection Act 2023. Where these terms are silent or in conflict with institutional policy, institutional policy governs.

## 11. Contact

Questions about these terms: **[email/office — fill in before publishing]**.

---

*Drafted from the actual behavior of the SmartAttend codebase as of 2026-09-04. Bracketed fields need to be filled in, and this document — like [PRIVACY.md](PRIVACY.md) — needs review by qualified counsel or your institution's own policy office before it is presented to real users as binding terms.*
