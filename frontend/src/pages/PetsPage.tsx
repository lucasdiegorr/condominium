import { useState } from "react";
import { scopedApi, type PersonView, type PetView } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { perm } from "../auth/permissions";
import { t } from "../i18n";
import { ErrorNote, Field, InlineForm, Loading, PageHeader, errorText, useScopedData } from "../components/ui";

export default function PetsPage() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission(perm.PETS_MANAGE);
  const canSelf = hasPermission(perm.PETS_SELF);

  const pets = useScopedData(() => scopedApi.listPets());
  const residents = useScopedData<PersonView[]>(
    () => (canManage ? scopedApi.listResidents() : Promise.resolve([])),
    [canManage],
  );

  const [name, setName] = useState("");
  const [species, setSpecies] = useState("");
  const [breed, setBreed] = useState("");
  const [residentId, setResidentId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate() {
    setBusy(true);
    setError(null);
    try {
      await scopedApi.createPet({
        name,
        species,
        breed: breed || null,
        resident_id: canManage ? Number(residentId) : null,
      });
      setName("");
      setSpecies("");
      setBreed("");
      setResidentId("");
      pets.reload();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  const writable = canManage || canSelf;

  return (
    <div>
      <PageHeader title={t("pets.title")} subtitle={t("pets.subtitle")} />
      {error ? <ErrorNote>{error}</ErrorNote> : null}

      {writable ? (
        <section className="card">
          <h3>{t("pets.addPet")}</h3>
          <InlineForm onSubmit={() => void handleCreate()} busy={busy} submitLabel={t("common.save")}>
            <Field label={t("pets.name")}>
              <input value={name} onChange={(e) => setName(e.target.value)} required />
            </Field>
            <Field label={t("pets.species")}>
              <input value={species} onChange={(e) => setSpecies(e.target.value)} required />
            </Field>
            <Field label={t("pets.breed")}>
              <input value={breed} onChange={(e) => setBreed(e.target.value)} />
            </Field>
            {canManage ? (
              <Field label={t("pets.resident")}>
                <select value={residentId} onChange={(e) => setResidentId(e.target.value)} required>
                  <option value="">{t("common.none")}</option>
                  {(residents.data ?? []).map((person) => (
                    <option key={person.id} value={person.id}>
                      {person.name}
                    </option>
                  ))}
                </select>
              </Field>
            ) : null}
          </InlineForm>
        </section>
      ) : null}

      {pets.loading ? (
        <Loading />
      ) : pets.error ? (
        <ErrorNote>{pets.error}</ErrorNote>
      ) : (
        <ul className="card-list">
          {(pets.data ?? []).map((pet) => (
            <PetRow
              key={pet.id}
              pet={pet}
              writable={writable}
              onChanged={pets.reload}
              onError={setError}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function PetRow({
  pet,
  writable,
  onChanged,
  onError,
}: {
  pet: PetView;
  writable: boolean;
  onChanged: () => void;
  onError: (message: string | null) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(pet.name);
  const [species, setSpecies] = useState(pet.species);
  const [breed, setBreed] = useState(pet.breed ?? "");
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    onError(null);
    try {
      await scopedApi.updatePet(pet.id, { name, species, breed: breed || null });
      setEditing(false);
      onChanged();
    } catch (err) {
      onError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!window.confirm(t("common.confirmDelete"))) return;
    setBusy(true);
    onError(null);
    try {
      await scopedApi.deletePet(pet.id);
      onChanged();
    } catch (err) {
      onError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="card">
      <div className="row-head">
        <strong>{pet.name}</strong>
        <span className="muted">
          {pet.species} · {pet.breed ?? t("common.none")}
        </span>
        {writable ? (
          <span className="row-actions">
            <button type="button" onClick={() => setEditing(!editing)}>
              {t("common.edit")}
            </button>
            <button type="button" onClick={() => void remove()}>
              {t("common.delete")}
            </button>
          </span>
        ) : null}
      </div>
      <p className="muted">{pet.resident_name}</p>
      {editing ? (
        <InlineForm onSubmit={() => void save()} busy={busy} submitLabel={t("common.save")}>
          <Field label={t("pets.name")}>
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
          <Field label={t("pets.species")}>
            <input value={species} onChange={(e) => setSpecies(e.target.value)} required />
          </Field>
          <Field label={t("pets.breed")}>
            <input value={breed} onChange={(e) => setBreed(e.target.value)} />
          </Field>
        </InlineForm>
      ) : null}
    </li>
  );
}
