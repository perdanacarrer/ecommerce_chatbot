describe("E-commerce Chatbot E2E", () => {
  beforeEach(() => {
    cy.visit("http://localhost:3000");
  });

  it("allows user to send a message and receive a reply", () => {
    cy.get("#messageInput")
      .type("Show me jackets under $50{enter}");

    cy.contains("Here are").should("exist");
  });

  it("renders product cards", () => {
    cy.get("#messageInput")
      .type("Show me jackets{enter}");

    cy.get(".card").should("have.length.at.least", 1);
  });

  it("supports comparison flow", () => {
    cy.get("#messageInput")
      .type("What's the difference between these jackets?{enter}");

    cy.contains("Which two products", { timeout: 8000 })
      .should("be.visible");

    cy.get("#messageInput")
      .type("Low Profile Dyed Cotton Twill Cap - Navy W39S55D and Enzyme Regular Solid Army Caps-Black W35S45D{enter}");

    cy.contains("Here’s a comparison", { timeout: 8000 })
      .should("be.visible");

    cy.get(".card").should("have.length.at.least", 1);
  });
});