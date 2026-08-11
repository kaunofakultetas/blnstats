// -----------------------------------------------------------
//  [*] AdministratorsListTable — the administrators DataGrid
//
//  The /admin/administrators page body: every account (id,
//  email, an enabled pill, last seen) in a DataGrid fed by a
//  TanStack query that is invalidated on every save, delete
//  and dialog close. A 401 bounces to /login.
//
//  MySQL's JSON_ARRAYAGG answers NULL — not [] — while no
//  account exists, hence `data ?? []`. DataGrid v8 renders
//  the toolbar slot only when `showToolbar` is set.
//
//  Split into (root component last):
//
//    StatusPill              — the colored Enabled/Disabled cell
//    ADMINISTRATORS_COLUMNS  — the column set
//    AdministratorsListTable — grid + dialog (default export)
//
//  Used by:
//    - AdministratorsList.jsx — the page body
// -----------------------------------------------------------

import { useEffect, useState } from "react";
import { DataGrid } from "@mui/x-data-grid";
import { useQuery, useQueryClient } from '@tanstack/react-query';
import axios from "axios";
import { Box, LinearProgress, Paper } from '@mui/material';

import PageTitle from '@/components/PageTitle/PageTitle';
import QuickSearchToolbar from '@/components/DatagridCustomComponents/QuickSearchToolbar';
import AddEditAdministrator from "./AddEditAdministrator/AddEditAdministrator";


const QUERY_KEY = ['admin-administrators'];







// -----------------------------------------------------------
// StatusPill
// -----------------------------------------------------------
//
// Used by:
//   - ADMINISTRATORS_COLUMNS (below)
// -----------------------------------------------------------

function StatusPill({ enabled }) {
  return (
    <div
      style={{
        backgroundColor: enabled === 1 ? 'green' : 'grey',
        borderRadius: 9,
        width: 80,
        textAlign: 'center',
      }}
    >
      {enabled === 1 ? 'Enabled' : 'Disabled'}
    </div>
  );
}







// -----------------------------------------------------------
// ADMINISTRATORS_COLUMNS
// -----------------------------------------------------------
//
// Module level: nothing here depends on component state, so
// the column set is not rebuilt on every render.
//
// Used by:
//   - AdministratorsListTable (below)
// -----------------------------------------------------------

const ADMINISTRATORS_COLUMNS = [
  {
    field: "id",
    headerName: "ID",
    width: 70
  },
  {
    field: "email",
    headerName: "Email",
    width: 350,
  },
  {
    field: "enabled",
    headerName: "Enabled",
    width: 100,
    renderCell: (params) => <StatusPill enabled={params.row.enabled} />,
  },
  {
    field: "lastseen",
    headerName: "Last seen",
    width: 220,
  },
];


export default function AdministratorsListTable() {

  const queryClient = useQueryClient();

  const { data, isPending: loadingData, error } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: async () => (await axios.get("/api/admin/administrators", { withCredentials: true })).data,
  });

  useEffect(() => {
    if (error?.response?.status === 401) {
      window.location.href = '/login';
    }
  }, [error]);

  const getData = () => queryClient.invalidateQueries({ queryKey: QUERY_KEY });


  // Both openers remember the rectangle of the element that
  // was clicked, so the dialog can fly out of it (see
  // UniversalModal)
  const [openBackdrop, setOpenBackdrop] = useState(false);
  const [userLineData, setUserLineData] = useState();
  const [modalSourceRect, setModalSourceRect] = useState(null);

  const handleRowClick = (params, event) => {
    setModalSourceRect(event?.currentTarget?.getBoundingClientRect() ?? null);
    setUserLineData({ ...params });
    setOpenBackdrop(true);
  };

  const triggerAddNew = (event) => {
    setModalSourceRect(event?.currentTarget?.getBoundingClientRect() ?? null);
    setUserLineData(undefined);
    setOpenBackdrop(true);
  };

  const handleDialogOpen = (value) => {
    setOpenBackdrop(value);
    if (value === false) {
      getData();
    }
  };


  return (
    <Paper className="w-full overflow-hidden" sx={{ paddingRight: 4, borderRadius: 0 }}>
      <Box sx={{ margin: 2, width: '100%' }}>
        <PageTitle>Administrators List</PageTitle>

        <DataGrid
          sx={{ height: 'calc(100vh - 185px)', cursor: 'pointer', backgroundColor: 'background.paper' }}
          rows={data ?? []}
          columns={ADMINISTRATORS_COLUMNS}
          rowHeight={30}
          pageSizeOptions={[100]}
          onRowClick={handleRowClick}
          showToolbar

          initialState={{
            columns: {
              columnVisibilityModel: {
              },
            },
            pagination: {
              paginationModel: { pageSize: 100 },
            },
          }}

          loading={loadingData}

          slots={{
            toolbar: QuickSearchToolbar,
            loadingOverlay: LinearProgress,
          }}
          slotProps={{
            toolbar: {
              onAddNew: triggerAddNew,
            }
          }}
        />
      </Box>

      {openBackdrop ?
        <AddEditAdministrator
          rowData={userLineData}
          setOpen={handleDialogOpen}
          getData={getData}
          sourceRect={modalSourceRect}
        />
        :
        <></>
      }
    </Paper>
  );
}
