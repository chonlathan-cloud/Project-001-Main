# FlowAccount API Quick Reference

Use this as a local quick reference for Projects-001. Verify current official docs before implementing fields that may have changed.

Official sources checked on 2026-06-16:

- https://developers.flowaccount.com/api-reference
- https://developers.flowaccount.com/swagger.yml
- https://developers.flowaccount.com/tutorial/connect/client-credentials-flow
- https://developers.flowaccount.com/tutorial/document-api/document-calculation-vat-company
- https://developers.flowaccount.com/tutorial/document-api/withholding-tax-feature/withholding-tax-simple-document
- https://developers.flowaccount.com/tutorial/document-api/supplier-invoice/reference

## Servers And Auth

- Sandbox: `https://openapi.flowaccount.com/test`
- Production: `https://openapi.flowaccount.com/v1`
- Token endpoint: `POST {base_url}/token`
- Content type: `application/x-www-form-urlencoded`
- Client credentials body:
  - `grant_type=client_credentials`
  - `scope=flowaccount-api`
  - `client_id`
  - `client_secret`
- Response contains `access_token`, `expires_in`, `token_type`, and `scope`.
- Client credentials tokens are generally valid for 86400 seconds. Cache until close to expiry.
- Token errors may return HTTP 200 with an `error` body such as `unsupported_grant_type`, `invalid_client`, or `invalid_scope`.

## Expense Endpoints

- `POST /expenses`: create simple expense. New expense starts as `awaiting`.
- `POST /expenses/inline`: create inline discount/VAT expense.
- `POST /expenses/{id}/attachment`: attach file as `multipart/form-data` with `file`.
- `POST /expenses/{id}/attachment/base64`: attach file as base64.
- `POST /expenses/{id}/payment`: mark expense paid.
- `POST /expenses/{id}/status/{statusId}`: status values include `awaiting`, `approved`, `received`, `void`.
- `GET /expenses/categories/business`: business-view expense categories.
- `GET /expenses/categories/accounting`: accounting-view expense categories.

Prefer multipart attachment when the backend can stream or download the stored receipt safely. Use base64 only if it simplifies GCS integration and file size remains acceptable.

## Expense Payload Notes

Common Expense document fields include:

- `contactName` required
- `contactAddress`, `contactTaxId`, `contactBranch`, `contactEmail`, `contactNumber`
- `publishedOn` date
- `projectName`
- `reference`
- `externalDocumentId`
- `isVatInclusive`
- `isVat`
- `subTotal`
- `discountAmount`
- `totalAfterDiscount`
- `vatAmount`
- `grandTotal`
- `remarks`
- `internalNotes`

Expense items require FlowAccount category/accounting ids. Do not assume item text is enough. Category-related fields include:

- `systemCode`
- `categoryId`
- `description`
- `nameLocal`
- `nameForeign`
- `creditId`
- `creditCategory`
- `debitId`
- `debitCategory`
- `quantity`
- `unitName`
- `pricePerUnit`
- `total`

Inline expense items add:

- `discountAmount`
- `vatRate` where `7 = VAT 7%`, `0 = VAT 0%`, and `-1 = VAT exempt`

For simple expenses, use document-level VAT. For mixed line-item VAT or preserving OCR lines with different VAT rates, use inline expense.

## VAT Calculation Policy

For a VAT registered company, FlowAccount supports:

- no VAT: `isVat=false`, `isVatInclusive=false`, `vatAmount=0`
- VAT exclusive: `isVat=true`, `isVatInclusive=false`
- VAT inclusive: `isVat=true`, `isVatInclusive=true`

Projects-001 user policy: `approved_amount` is whatever appears on the receipt. Confirm per request whether that amount is inclusive, exclusive, or no VAT before syncing.

## Withholding Tax

Simple documents support document-level WHT:

- `documentShowWithholdingTax`
- `documentWithholdingTaxPercentage`
- `documentWithholdingTaxAmount`

If `documentShowWithholdingTax=false`, percentage and amount must be `0`.

Projects-001 user policy:

- Labor defaults to 3% WHT.
- Labor `approved_amount` is the net amount actually paid to the subcontractor.
- Material, advance payment, and general expense default to no WHT.

When only net payment is stored, calculate the gross/WHT fields carefully and make the calculation visible in readiness/review if there is ambiguity.

## Expense Payment

Use `POST /expenses/{id}/payment` with a `PaymentPaidDocument` variant.

Common payment fields:

- `paymentDate` required
- `collected` required and non-zero
- `withheldPercentage`
- `withheldAmount`
- `paymentRemarks`
- `remainingCollectedType`
- `remainingCollected`

Payment methods include:

- `1`: cash
- `3`: cheque
- `5`: transfer
- credit card, petty cash, and other channels are also supported through specific schema variants

Projects-001 user policy: default payment method is transfer. Transfer requires a FlowAccount bank channel id.

Bank channel endpoints:

- `GET /bank-channel/bank-accounts`
- `GET /bank-channel/cheque`
- `GET /bank-channel/credit-card`
- `GET /bank-channel/petty-cash`
- `GET /bank-channel/other-channels`

For transfer payments, configure the default FlowAccount `bankAccountId` in backend env/config.

## Supplier Invoice / Input VAT

Use Supplier Invoice/input VAT handling when the user needs proper VAT tax filing, not just a receipt attachment.

Supplier Invoice reference fields include:

- `documentSerial`: tax invoice number, required
- `contactName`: supplier name, required
- `contactBranch`: supplier branch, required
- `documentDate`: tax invoice date
- `contactTaxId`: required for P.P.30 and must be 13 digits when supplied
- `taxForm`: `1` for P.P.30 by default, `3` for P.P.36
- `vatableAmount`: conditional
- `vatAmount`: conditional
- `file.fileName`
- `file.base64Data`

Related enum from the docs:

- `documentType=18`: Expense
- `documentType=19`: Purchase

Supplier Invoice file constraints:

- max 1 file
- max 10 MB
- supported extensions include `jpg`, `jpeg`, `png`, `bmp`, `tif`, `tiff`, `pdf`, `doc`, `docx`, `xls`, `xlsx`, `ppt`, `pptx`

Projects-001 default assumption: use `taxForm=1` P.P.30 for Thai supplier tax invoices unless the Owner/accounting policy says otherwise.

## Recommended Config Names

Use env values or a backend settings table; never hardcode secrets.

Core:

- `FLOWACCOUNT_BASE_URL`
- `FLOWACCOUNT_CLIENT_ID`
- `FLOWACCOUNT_CLIENT_SECRET`
- `FLOWACCOUNT_SCOPE=flowaccount-api`
- `FLOWACCOUNT_TOKEN_CACHE_SECONDS`
- `FLOWACCOUNT_ENABLED`

Payment:

- `FLOWACCOUNT_DEFAULT_PAYMENT_METHOD=transfer`
- `FLOWACCOUNT_DEFAULT_BANK_ACCOUNT_ID`

Mapping:

- Use a JSON mapping or settings table from Projects-001 request type to FlowAccount category fields.
- Include material, labor, advance payment, and general expense.
- Include VAT/WHT defaults and whether Supplier Invoice is required.

## Error Handling

- Treat HTTP non-2xx as failure.
- Treat `status=false`, non-zero `code`, or `error` response bodies as failure even if HTTP status is 200.
- Store a safe user message in sync state.
- Log raw response detail only in protected backend logs.
- Never expose access tokens, client secrets, signed GCS URLs, or raw receipt URLs in frontend error messages.
