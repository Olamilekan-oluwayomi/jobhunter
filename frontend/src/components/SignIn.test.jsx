import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SignIn from "./SignIn";
import { login, register } from "../api/auth";

vi.mock("../api/auth", () => ({ login: vi.fn(), register: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

async function fill() {
  await userEvent.type(screen.getByLabelText("Email"), "alice@example.com");
  await userEvent.type(
    screen.getByLabelText("Password"),
    "a long test password",
  );
}

it("signs in and returns the account to the workspace", async () => {
  const onSuccess = vi.fn();
  login.mockResolvedValue({ id: 2, email: "alice@example.com" });
  render(<SignIn onSuccess={onSuccess} />);
  await fill();
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect(onSuccess).toHaveBeenCalledWith({ id: 2, email: "alice@example.com" });
});

it("supports registration without submitting a sign-in request", async () => {
  register.mockResolvedValue({ id: 3 });
  render(<SignIn onSuccess={vi.fn()} />);
  await userEvent.click(
    screen.getByRole("button", { name: "Create an account" }),
  );
  await fill();
  await userEvent.click(screen.getByRole("button", { name: "Create account" }));
  expect(register).toHaveBeenCalledWith({
    email: "alice@example.com",
    password: "a long test password",
  });
  expect(login).not.toHaveBeenCalled();
});

it("keeps the form available after an authentication failure", async () => {
  login.mockRejectedValue({
    response: { data: { detail: "Email or password is incorrect" } },
  });
  const onSuccess = vi.fn();
  render(<SignIn onSuccess={onSuccess} />);
  await fill();
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    "Email or password is incorrect",
  );
  expect(onSuccess).not.toHaveBeenCalled();
});
