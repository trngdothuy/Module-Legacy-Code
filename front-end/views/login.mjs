import {renderOne, destroy} from "../lib/render.mjs";
import {state, getLoginContainer} from "../index.mjs";
import {createLogin, handleLogin} from "../components/login.mjs";

// Initial load - not logged in
function loginView() {
  console.log("loginView called");
  destroy();
  renderOne(
    state.isLoggedIn,
    getLoginContainer(),
    "login-template",
    createLogin
  );
  console.log("loginView rendered", getLoginContainer());

  
  const form = document.querySelector("[data-form='login']");
  console.log("loginView form", form);
  
  form?.addEventListener("submit", handleLogin);
}

export {loginView};
