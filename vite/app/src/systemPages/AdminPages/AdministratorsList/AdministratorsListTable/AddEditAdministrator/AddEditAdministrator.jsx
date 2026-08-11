// -----------------------------------------------------------
//  [*] AddEditAdministrator — the administrator dialog
//
//  One POST endpoint, /api/admin/administrators, does both
//  insertupdate and delete via the `action` field; an empty
//  password keeps the stored hash, and admin is always 1
//  since every account here is an administrator. It answers
//  { type: "ok" | "error", reason }, shown as a toast.
//
//  The table mounts this dialog conditionally, so closing must
//  go through UniversalModal's closeRef: setOpen(false) alone
//  unmounts us mid-flight, cutting the return animation.
//
//  Split into (root component last):
//
//    blankAdministrator   — the empty form state
//    ModalActions         — Save/Insert + Delete bar
//    FormFields           — id/email/enabled/password inputs
//    AddEditAdministrator — state + API calls (default export)
//
//  Used by:
//    - AdministratorsListTable — row click (edit) and Add new
//      (create)
// -----------------------------------------------------------

import { useEffect, useRef, useState } from "react";
import axios from "axios";
import toast from 'react-hot-toast';
import { Box, Button, FormControl, MenuItem, Stack, TextField } from "@mui/material";

import DeleteIcon from '@mui/icons-material/Delete';

import { UniversalModal } from '@/components/UniversalModal';
import { LongPressDeleteButton } from '@/components/LongPressButton';







// -----------------------------------------------------------
// blankAdministrator
// -----------------------------------------------------------
//
// The form state a fresh Add new dialog opens with: enabled
// and admin already 1, every text field empty.
//
// Used by:
//   - AddEditAdministrator (below) — the insert case
// -----------------------------------------------------------

const blankAdministrator = () => ({
  id: '',
  email: '',
  enabled: 1,
  password: '',
  confirmPassword: '',
  admin: 1,
});







// -----------------------------------------------------------
// ModalActions
// -----------------------------------------------------------
//
// Deleting an account cannot be undone, so Delete is
// hold-to-confirm rather than a plain click.
//
// Used by:
//   - AddEditAdministrator (below) — the `actions` prop
// -----------------------------------------------------------

function ModalActions({ isEditing, disableSave, onSave, onDelete }) {
  return (
    <div className="flex gap-2">
      {/* Backgrounds live in sx only, never split between an sx
          color and a Tailwind class: StyledEngineProvider in
          App.jsx makes Tailwind win, so a split declaration is
          ambiguous. */}
      <Button
        type="submit"
        className="flex-1 shadow-[0px_8px_15px_rgba(0,0,0,0.1)]"
        sx={{
          backgroundColor: disableSave ? 'gray' : 'primary.main',
          color: 'white',
          '&:hover': {
            backgroundColor: disableSave ? 'gray' : 'primary.accent'
          }
        }}
        onClick={onSave}
        disabled={disableSave}
      >
        {isEditing ? 'Save' : 'Insert'}
      </Button>

      {isEditing && (
        <LongPressDeleteButton
          fullWidth
          sx={{ flex: 1, boxShadow: '0px 8px 15px rgba(0,0,0,0.1)' }}
          onComplete={onDelete}
          uncompletedToastMessage="Hold the button to delete"
        >
          <DeleteIcon sx={{ mr: 1 }} />
          Delete Record
        </LongPressDeleteButton>
      )}
    </div>
  );
}







// -----------------------------------------------------------
// FormFields
// -----------------------------------------------------------
//
// The stacked inputs: read-only ID, email, the Enabled
// select, and the password pair — hidden in edit mode until
// "Change Password" is pressed.
//
// Used by:
//   - AddEditAdministrator (below) — the modal children
// -----------------------------------------------------------

function FormFields({ data, setData, isEditing, changePassword, setChangePassword, passwordsMatch }) {
  return (
    <Stack spacing={3}>
      <FormControl color="primary">
        <TextField
          disabled
          sx={{ backgroundColor: "lightgrey" }}
          label="ID"
          value={data.id}
        />
      </FormControl>

      <FormControl color="primary">
        <TextField
          type="email"
          required
          label="Email"
          value={data.email}
          onChange={(e) => setData(prevData => ({ ...prevData, email: e.target.value }))}
        />
      </FormControl>

      <FormControl color="primary">
        <TextField
          select
          label="Enabled"
          value={data.enabled}
          onChange={(e) => setData(prevData => ({ ...prevData, enabled: e.target.value }))}
        >
          <MenuItem value={1}>Yes</MenuItem>
          <MenuItem value={0}>No</MenuItem>
        </TextField>
      </FormControl>

      {isEditing && !changePassword && (
        <Box>
          <Button
            variant="outlined"
            onClick={() => setChangePassword(true)}
            className="w-full text-black mb-[10px]"
          >
            Change Password
          </Button>
        </Box>
      )}

      {(changePassword || !isEditing) && (
        <>
          <FormControl color="primary">
            <TextField
              type="password"
              label="Password"
              value={data.password}
              onChange={(e) => setData(prevData => ({ ...prevData, password: e.target.value }))}
            />
          </FormControl>

          <FormControl color="primary">
            <TextField
              type="password"
              label="Confirm Password"
              value={data.confirmPassword}
              error={!passwordsMatch && data.confirmPassword !== ''}
              helperText={!passwordsMatch && data.confirmPassword !== '' ? 'Passwords do not match' : ''}
              onChange={(e) => setData(prevData => ({ ...prevData, confirmPassword: e.target.value }))}
            />
          </FormControl>
        </>
      )}
    </Stack>
  );
}







// -----------------------------------------------------------
// AddEditAdministrator (default export)
// -----------------------------------------------------------
//
// Holds the form state and the POST. Renders nothing until
// the effect has seeded the form from rowData (edit) or the
// blank (insert), so the fields never flash stale values.
//
// Used by:
//   - AdministratorsListTable — row click (edit) and the
//     toolbar's Add new (create)
// -----------------------------------------------------------

export default function AddEditAdministrator({ rowData, setOpen, getData, sourceRect }) {

  const [data, setData] = useState(undefined);
  const [changePassword, setChangePassword] = useState(false);

  const modalCloseRef = useRef(null);

  const isEditing = rowData !== undefined;


  useEffect(() => {
    if (rowData !== undefined) {
      setData({
        id: rowData.row.id,
        email: rowData.row.email,
        enabled: rowData.row.enabled,
        password: '',
        confirmPassword: '',
        admin: 1,
      });
      setChangePassword(false);
    } else {
      setData(blankAdministrator());
      setChangePassword(true);
    }
  }, [rowData]);


  // The grid refreshes and the dialog closes whatever the
  // answer was; a rejected save leaves its reason in the toast.
  // BUG (backend, documented not fixed): inserts use INSERT
  // IGNORE, so a duplicate email answers { type: 'ok' } and the
  // toast says Saved although no row was created.
  async function sendData(postData) {
    try {
      const response = await axios.post("/api/admin/administrators", postData, { withCredentials: true });

      if (response.data.type === 'ok') {
        toast.success(<b>Saved</b>, { duration: 3000 });
      } else if (response.data.type === 'error') {
        toast.error(<b>Failed:<br />{response.data.reason}</b>, { duration: 8000 });
      } else {
        toast.error(<b>Failed:<br />Unknown response.</b>, { duration: 8000 });
      }
    } catch (error) {
      toast.error(<b>Failed:<br />{error.message}</b>, { duration: 8000 });
    }

    getData();
    modalCloseRef.current?.();
  }


  function handleSaveButton() {
    sendData({
      action: 'insertupdate',
      id: data.id,
      email: data.email,
      enabled: data.enabled,
      password: data.password,
      admin: 1,
    });
  }


  function handleDeleteButton() {
    sendData({
      action: 'delete',
      id: data.id,
    });
  }


  if (data === undefined) {
    return null;
  }


  const passwordsMatch = data.password === data.confirmPassword;

  // Inserting, or editing with "Change Password" pressed,
  // needs two matching non-empty passwords; editing without
  // touching them leaves both empty, which is allowed.
  // Non-empty is also all the backend enforces — its "at least
  // 8 characters" error message only fires on an empty one.
  const disableSave =
    (changePassword && (!passwordsMatch || data.password === '' || data.confirmPassword === '')) ||
    (data.email.trim() === '');


  return (
    <UniversalModal
      open={true}
      onClose={() => setOpen(false)}
      closeRef={modalCloseRef}
      title="Administrator"
      sourceRect={sourceRect}
      maxWidth={500}
      fullWidth
      showCancel={false}
      showConfirm={false}
      actions={
        <ModalActions
          isEditing={isEditing}
          disableSave={disableSave}
          onSave={handleSaveButton}
          onDelete={handleDeleteButton}
        />
      }
    >
      <FormFields
        data={data}
        setData={setData}
        isEditing={isEditing}
        changePassword={changePassword}
        setChangePassword={setChangePassword}
        passwordsMatch={passwordsMatch}
      />
    </UniversalModal>
  );
}
