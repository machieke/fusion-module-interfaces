use detta_da::*;
use detta_storage::FileStorage;
use serde::Deserialize;
use serde_json::{json, Value};
use std::io::{self, Read};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    operation: String,
    root: String,
    scope_hash: String,
    key: Option<String>,
    bytes: Option<Vec<u8>>,
    manifest: Option<String>,
}

fn profile() -> Result<DaApplicationProfile, String> {
    let ns = DaNamespace::new("opaque.records").map_err(debug)?;
    let profile = DaApplicationProfile {
        schema: DA_APPLICATION_PROFILE_SCHEMA.into(),
        schema_version: 1,
        application_id: DaApplicationId::new("opaque.storage").map_err(debug)?,
        profile_version: 1,
        profile_name: "Opaque local storage fixture".into(),
        da_profile: DaProductionProfile::v1(),
        namespace_policies: vec![DaNamespacePolicy {
            namespace: ns.clone(),
            requirement: DaNamespaceRequirement::Required,
            allowed_record_schemas: vec!["opaque.bytes".into()],
            min_records: 1,
            max_records: 1,
            retention_class: DaApplicationRetentionClass::Archive,
        }],
        record_policies: vec![DaRecordPolicy {
            schema: "opaque.bytes".into(),
            schema_version: 1,
            allowed_namespaces: vec![ns],
            allowed_encodings: vec![DaRecordEncoding::OpaqueBytes],
            max_record_bytes: 65536,
            require_content_hash: true,
            require_signer: false,
        }],
        coordinate_policy: DaCoordinatePolicy {
            max_stream_id_bytes: 128,
            allow_epoch: false,
            require_parent_hash: false,
            require_subject_hash: true,
        },
        root_bindings: vec![],
        retention_policy: DaApplicationRetentionPolicy {
            default_class: DaApplicationRetentionClass::Archive,
            namespace_overrides: vec![],
            payload_kind_overrides: vec![],
        },
        validation_mode: DaApplicationValidationMode::OpaqueBytes,
        privacy_mode: DaApplicationPrivacyMode::Public,
        max_payload_bytes: 524288,
        max_records_per_payload: 1,
    }
    .canonicalized();
    profile.validate().map_err(debug)?;
    Ok(profile)
}

fn debug(e: impl std::fmt::Debug) -> String {
    format!("{e:?}")
}

fn run(r: Request) -> Result<Value, String> {
    if r.scope_hash.len() != 64 || !r.scope_hash.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err("invalid scope".into());
    }
    let store = FileStorage::open(&r.root).map_err(debug)?;
    let p = profile()?;
    match r.operation.as_str() {
        "put" => {
            let bytes = r.bytes.ok_or("bytes required")?;
            if bytes.is_empty() || bytes.len() > 65536 {
                return Err("payload bounds".into());
            }
            let key = r.key.ok_or("key required")?;
            let record = DaRecordEnvelope::new(
                "opaque.bytes",
                1,
                "application/octet-stream",
                DaRecordEncoding::OpaqueBytes,
                bytes,
                None,
                None,
            )
            .map_err(debug)?;
            let payload = ApplicationDaPayload::new(
                &p,
                DaApplicationCoordinate {
                    application_id: p.application_id.clone(),
                    stream_id: key,
                    sequence: 1,
                    epoch: None,
                    parent_hash: None,
                    subject_hash: Some(r.scope_hash.clone()),
                },
                DaPayloadKind::Batch,
                None,
                vec![],
                vec![ApplicationDaNamespaceSection::new(
                    DaNamespace::new("opaque.records").map_err(debug)?,
                    vec![record],
                )
                .map_err(debug)?],
            )
            .map_err(debug)?;
            let set = ApplicationDaShareSet::from_payload_reed_solomon(&payload, &p, 4, 2)
                .map_err(debug)?;
            store
                .commit_application_da_profile_registration(
                    &DaApplicationProfileRegistration::active(p.clone()).map_err(debug)?,
                )
                .map_err(debug)?;
            let manifest = store
                .commit_application_da_share_set(&set, &p)
                .map_err(debug)?;
            Ok(
                json!({"manifest": manifest, "profile": p.profile_id().map_err(debug)?,
                "payload_hash": set.manifest.payload_hash, "payload_bytes": set.manifest.payload_bytes,
                "shares": 6, "threshold": 4, "custody_certificate": null, "chain": null}),
            )
        }
        "get" | "availability" => {
            let id = r.manifest.ok_or("manifest required")?;
            if id.len() != 64 || !id.bytes().all(|b| b.is_ascii_hexdigit()) {
                return Err("invalid manifest".into());
            }
            let manifest = store
                .maybe_load_application_da_manifest(&id)
                .map_err(debug)?
                .ok_or("NOT_FOUND")?;
            if manifest.coordinate.subject_hash.as_ref() != Some(&r.scope_hash) {
                return Err("UNAUTHORIZED".into());
            }
            let mut shares = vec![];
            for index in 0..manifest.encoded_share_count {
                if let Some(share) = store
                    .maybe_load_application_da_share(&id, index)
                    .map_err(debug)?
                {
                    shares.push(share);
                }
            }
            let count = shares.len();
            let set = ApplicationDaShareSet { manifest, shares };
            let payload = set.reconstruct_payload(&p).map_err(debug)?;
            let record = &payload.namespaces[0].records[0];
            Ok(
                json!({"bytes": if r.operation == "get" { Some(&record.bytes) } else { None },
                "available": true, "present_shares": count, "threshold": 4,
                "content_hash": record.content_hash}),
            )
        }
        _ => Err("UNSUPPORTED_OPERATION".into()),
    }
}

fn main() {
    let mut input = String::new();
    let result = io::stdin()
        .take(524289)
        .read_to_string(&mut input)
        .map_err(debug)
        .and_then(|_| {
            if input.len() > 524288 {
                return Err("request too large".into());
            }
            serde_json::from_str(&input).map_err(debug).and_then(run)
        });
    let output = match result {
        Ok(value) => json!({"ok": value}),
        Err(error) => json!({"error": if error == "NOT_FOUND" { "NOT_FOUND" }
            else if error == "UNAUTHORIZED" { "UNAUTHORIZED" }
            else if error == "UNSUPPORTED_OPERATION" { "UNSUPPORTED_OPERATION" }
            else { "NOT_AVAILABLE" }}),
    };
    println!("{output}");
}
