"""Random life events (one per quarter) and how their options are applied."""

import math

from ..formatting import esc, money
from .actions import MoneyMoves


class LifeEvents(MoneyMoves):
    """The event deck, the event builders and option handling."""

    # -------------------------------------------------------------- events --
    def _draw_event_key(self):
        while self.scripted_events:
            key = self.scripted_events.pop(0)
            if self._event_applies(key):
                return key
        if self.age_months == 9 and self.rng.random() < 0.5 and self.last_event_key != "holiday":
            return "holiday"
        for _ in range(sum(self.EVENT_DECK.values()) * 2):
            if not self.event_deck:
                self.event_deck = [k for k, n in self.EVENT_DECK.items() for _ in range(n)]
                self.rng.shuffle(self.event_deck)
            key = self.event_deck.pop()
            if key == self.last_event_key or not self._event_applies(key):
                continue
            return key
        return "festival"

    def _event_applies(self, key):
        if key == "course":
            return self.courses_taken < self.MAX_COURSES
        if key in ("accident",):
            return self.has_car
        if key == "pet":
            return not self.has_pet
        if key == "limit_offer":
            return self.credit_score >= 600 and self.limit_bonus < 6000
        if key == "dip":
            return self.investments >= 500
        if key == "debt_offer":
            return self.card + self.loans > 0
        if key == "layoff":
            return self.layoff_turns == 0
        if key == "inheritance":
            return not self.inheritance_done
        return True

    def _trigger_event(self):
        key = self._draw_event_key()
        self.last_event_key = key
        ev = getattr(self, f"_ev_{key}")()
        ev["key"] = key
        self.current_event = ev
        self.state = "event"

    @staticmethod
    def O(label, pay=None, amount=0, tone="skip", log="", need=0, **fx):
        return {"label": label, "pay": pay, "amount": int(amount), "tone": tone,
                "log": log, "need": int(need), "fx": fx}

    def _collect_option(self, amt, what):
        return self.O("Ignore the bill — it goes to collections (+15% fee, -50 credit)",
                      "collections", amt, "bad", log=what)

    def _loan_label(self, amt):
        return f"Payment plan: {money(amt)} bank loan at {self.loan_rate():.2%}/qtr"

    def _ev_festival(self):
        c = self.price(450)
        return {"title": "Weekend Music Festival",
                "desc": "Your friends are heading to a 3-day music festival to recharge. Missing it will sting.",
                "options": [
                    self.O(f"Pay {money(c)} cash  (+18 happiness)", "cash", c, "cash", "Went to the festival", happiness=18),
                    self.O(f"Charge {money(c)} to credit card  (+18 happiness)", "card", c, "card", "Charged the festival", happiness=18),
                    self.O("Stay home  (-12 happiness)", None, 0, "skip", "Skipped the festival", happiness=-12)]}

    def _ev_market(self):
        a, b = self.price(1000), self.price(2000)
        return {"title": "Index Fund Opportunity",
                "desc": "A low-fee index fund is open to new investors. Investing early lets compounding work for decades — "
                        "but markets can fall, and borrowed money charges interest even when they do.",
                "options": [
                    self.O(f"Invest {money(a)} cash", "cash", a, "cash", f"Invested {money(a)} in an index fund", invest=a),
                    self.O(f"Borrow {money(b)} to invest (loan at {self.loan_rate():.2%}/qtr)", "loan", b, "loan",
                           f"Borrowed {money(b)} to invest", invest=b),
                    self.O("Pass", None, 0, "skip", "Passed on the index fund")]}

    def _ev_car(self):
        if self.has_car:
            c, s = self.price(700), self.price(1500)
            return {"title": "Car Trouble",
                    "desc": "Your car's transmission is slipping. Without a car your commute gets harder and your pay drops 10%.",
                    "options": [
                        self.O(f"Repair it: {money(c)} cash", "cash", c, "cash", "Repaired the car"),
                        self.O(f"Repair it: charge {money(c)} to card", "card", c, "card", "Charged the car repair"),
                        self.O(f"Sell the car (+{money(s)}, -10% pay, cheaper transport)", None, 0, "bad",
                               f"Sold the car for {money(s)}", cash=s, has_car=False)]}
        c = self.price(3000)
        return {"title": "Commute Struggles",
                "desc": "Bus delays are wrecking your schedule. A used car would restore your full pay.",
                "options": [
                    self.O(f"Buy a used car: {money(c)} cash", "cash", c, "cash", "Bought a used car", has_car=True),
                    self.O(f"Finance it: {money(c)} loan at {self.loan_rate():.2%}/qtr", "loan", c, "loan", "Financed a used car", has_car=True),
                    self.O("Keep taking the bus  (-10 happiness)", None, 0, "skip", "Stuck with the bus", happiness=-10)]}

    def _ev_vacation(self):
        c, w = self.price(1300), self.wage(600)
        return {"title": "Beach Vacation",
                "desc": "A week at the beach would do wonders for your mood — or you could pick up overtime instead.",
                "options": [
                    self.O(f"Book it: {money(c)} cash  (+30 happiness)", "cash", c, "cash", "Took a beach vacation", happiness=30),
                    self.O(f"Charge {money(c)} to card  (+30 happiness)", "card", c, "card", "Charged a beach vacation", happiness=30),
                    self.O(f"Work overtime instead  (+{money(w)}, -12 happiness)", None, 0, "good",
                           f"Worked overtime (+{money(w)})", cash=w, happiness=-12)]}

    def _ev_course(self):
        c = self.price(self.COURSE_BASE_COST * (1.35 ** self.courses_taken))
        b = self.wage(self.COURSE_BONUS)
        q = math.ceil(c / max(1, b * (1 - self.LIFESTYLE_CREEP)))
        return {"title": "Career Certification",
                "desc": f"Certification {self.courses_taken + 1} of {self.MAX_COURSES}: permanently raises your pay by "
                        f"{money(b)}/qtr. After lifestyle creep it pays for itself in about {q} quarters.",
                "options": [
                    self.O(f"Pay {money(c)} cash", "cash", c, "cash", "Completed a certification", course=True),
                    self.O(f"Charge {money(c)} to card", "card", c, "card", "Completed a certification (on card)", course=True),
                    self.O(f"Student loan: {money(c)} at {self.loan_rate():.2%}/qtr", "loan", c, "loan",
                           "Completed a certification (student loan)", course=True),
                    self.O("Skip it", None, 0, "skip", "Skipped the certification")]}

    def _ev_credit_quiz(self):
        if not self.quiz_pool:
            self.quiz_pool = list(range(len(self.QUIZ)))
            self.rng.shuffle(self.quiz_pool)
        q, answers, explain = self.QUIZ[self.quiz_pool.pop()]
        order = list(range(3))
        self.rng.shuffle(order)
        opts = [self.O(answers[i], None, 0, "info", "", quiz=(i == 0)) for i in order]
        return {"title": "Credit Workshop Quiz",
                "desc": f"A free community credit workshop ends with a quick question. Answer correctly to win a "
                        f"{money(int(round(self.price(150), -1)))} gift card.\n\n{q}",
                "explain": explain, "options": opts}

    def _ev_layoff(self):
        s = self.wage(1500)
        return {"title": "Company Layoffs",
                "desc": "Your company is downsizing and your role is cut. This is exactly why an emergency fund "
                        "(3-6 months of essentials) matters.",
                "options": [
                    self.O(f"Take severance: +{money(s)} now, 50% pay for 2 quarters", None, 0, "loan",
                           f"Laid off with {money(s)} severance", cash=s, layoff=(2, 0.5)),
                    self.O("Take a temp contract: 75% pay for 2 quarters", None, 0, "skip",
                           "Took a temp contract", layoff=(2, 0.75))]}

    def _ev_medical(self):
        c = self.price(1400)
        return {"title": "Medical Emergency",
                "desc": f"A trip to the ER leaves you with a {money(c)} bill. This one isn't optional.",
                "options": [
                    self.O(f"Pay {money(c)} cash", "cash", c, "cash", "Paid the hospital bill"),
                    self.O(f"Charge {money(c)} to card", "card", c, "card", "Charged the hospital bill"),
                    self.O(self._loan_label(c), "loan", c, "loan", "Hospital payment plan"),
                    self._collect_option(c, "Hospital bill")]}

    def _ev_phone(self):
        new, used = self.price(900), self.price(300)
        return {"title": "Phone Smashed",
                "desc": "Your phone slipped and the screen is shattered beyond repair.",
                "options": [
                    self.O(f"New flagship phone: charge {money(new)} to card  (+5 happiness)", "card", new, "card",
                           "Bought a new phone on card", happiness=5),
                    self.O(f"Refurbished phone: {money(used)} cash", "cash", used, "cash", "Bought a refurbished phone"),
                    self.O("Go without a phone  (-12 happiness)", None, 0, "skip", "Went without a phone", happiness=-12)]}

    def _ev_rent_hike(self):
        hike, move = 250, self.price(900)
        opts = [self.O(f"Accept the increase (+{money(self.price(hike))}/qtr rent forever)", None, 0, "bad",
                       "Accepted a rent increase", rent=hike)]
        if not self.has_roommate:
            opts.append(self.O(f"Get a roommate (rent -{money(self.price(300))}/qtr, -15 happiness)", None, 0, "good",
                               "Got a roommate", rent=-300, roommate=True, happiness=-15))
        opts += [self.O(f"Move somewhere cheaper: {money(move)} cash moving costs (-8 happiness)", "cash", move, "cash",
                        "Moved to avoid the rent hike", happiness=-8),
                 self.O(f"Move: charge {money(move)} moving costs to card (-8 happiness)", "card", move, "card",
                        "Moved (moving costs on card)", happiness=-8)]
        return {"title": "Rent Increase",
                "desc": f"Your landlord is raising rent by {money(self.price(hike))} per quarter, permanently.",
                "options": opts}

    def _ev_side_hustle(self):
        w = self.wage(700)
        return {"title": "Weekend Side Hustle",
                "desc": "A friend needs help with weekend deliveries for the next few months.",
                "options": [
                    self.O(f"Take the gig  (+{money(w)}, -12 happiness)", None, 0, "good", f"Side hustle +{money(w)}",
                           cash=w, happiness=-12),
                    self.O("Decline — protect your weekends", None, 0, "skip", "Declined the side hustle")]}

    def _ev_wedding(self):
        c = self.price(700)
        return {"title": "Friend's Wedding",
                "desc": "Your close friend is getting married out of town. Travel, hotel and a gift add up.",
                "options": [
                    self.O(f"Go: {money(c)} cash  (+10 happiness)", "cash", c, "cash", "Went to the wedding", happiness=10),
                    self.O(f"Go: charge {money(c)} to card  (+10 happiness)", "card", c, "card", "Charged the wedding trip", happiness=10),
                    self.O("Send regrets  (-15 happiness)", None, 0, "skip", "Missed the wedding", happiness=-15)]}

    def _ev_tax_refund(self):
        r = self.wage(900)
        opts = [self.O(f"Save it (+{money(r)} cash)", None, 0, "cash", f"Saved a {money(r)} tax refund", cash=r),
                self.O(f"Invest it (+{money(r)} investments)", None, 0, "info", f"Invested a {money(r)} tax refund", invest=r)]
        if self.card + self.loans > 0:
            opts.append(self.O(f"Put it toward debt ({money(r)})", None, 0, "good", "Paid debt with the tax refund", cash=r, pay_debt=r))
        opts.append(self.O("Treat yourself (+20 happiness)", None, 0, "card", "Splurged the tax refund", happiness=20))
        return {"title": "Tax Refund", "desc": f"You overpaid taxes last year and got {money(r)} back.", "options": opts}

    def _ev_limit_offer(self):
        return {"title": "Credit Limit Increase",
                "desc": "Thanks to your good payment record, the bank offers to raise your card limit by $2,000.",
                "info": "A higher limit gives you more room for emergencies so surprise bills don't hit overdraft or "
                        "collections. In this game, using your card never hurts your score — only unpaid minimums do. "
                        "The risk is temptation: more credit makes overspending easier.",
                "options": [
                    self.O("Accept (+$2,000 card limit)", None, 0, "card", "Card limit raised by $2,000", limit_bonus=2000),
                    self.O("Decline", None, 0, "skip", "Declined a limit increase")]}

    def _ev_identity_theft(self):
        f = self.price(800)
        return {"title": "Suspicious Charges!",
                "desc": f"{money(f)} of purchases you never made just showed up on your credit card.",
                "info": "Always read your statements. Reporting fraud quickly gets charges reversed — ignoring it means "
                        "you're stuck paying them (plus interest).",
                "options": [
                    self.O("Report it to your bank right away (charges reversed, -5 happiness hassle)", None, 0, "good",
                           "Reported fraud — charges reversed", happiness=-5),
                    self.O(f"Ignore it (the {money(f)} stays on your card)", None, 0, "bad",
                           f"Ignored fraud — {money(f)} stays on the card", card_charge=f)]}

    def _ev_pet(self):
        c = self.price(600)
        return {"title": "Adopt a Dog?",
                "desc": f"A shelter puppy picked you. Adoption costs {money(c)}, food & vet add "
                        f"{money(self.price(self.PET_COST))}/qtr forever — but your happiness decays 3 less per quarter.",
                "options": [
                    self.O(f"Adopt: {money(c)} cash  (+25 happiness)", "cash", c, "cash", "Adopted a dog!", happiness=25, pet=True),
                    self.O(f"Adopt: charge {money(c)} to card  (+25 happiness)", "card", c, "card", "Adopted a dog (on card)", happiness=25, pet=True),
                    self.O("Not right now", None, 0, "skip", "Didn't adopt")]}

    def _ev_review(self):
        r = self.wage(450)
        chance = min(0.85, 0.45 + 0.08 * self.courses_taken)
        return {"title": "Performance Review",
                "desc": f"Annual review time. Your certifications give you a {int(chance * 100)}% chance if you ask for a raise.",
                "options": [
                    self.O(f"Ask for a raise (+{money(r)}/qtr if it works, -5 happiness if not)", None, 0, "good", "",
                           gamble=(chance, {"income": 450, "log": f"Raise approved! +{money(r)}/qtr"},
                                   {"happiness": -5, "log": "Raise request denied"})),
                    self.O(f"Volunteer for a big project (+{money(self.wage(300))}/qtr, -15 happiness)", None, 0, "loan",
                           "Took on extra responsibility", income=300, happiness=-15),
                    self.O("Keep your head down", None, 0, "skip", "Quiet review")]}

    def _ev_crypto(self):
        c = self.price(1000)
        return {"title": "Crypto Hype",
                "desc": "A coworker swears a new coin will 'definitely 10x'. He wants you in today.",
                "info": "High-risk speculation is not investing. Never put in money you can't afford to lose — and "
                        "never borrow to gamble.",
                "options": [
                    self.O(f"Buy {money(c)} of the coin (cash)", "cash", c, "bad", "",
                           gamble=(0.30, {"cash": c * 3, "log": f"The coin mooned! Sold for {money(c * 3)}"},
                                   {"cash": c // 10, "log": f"The coin crashed 90%. Recovered {money(c // 10)}"})),
                    self.O("Pass — stick to what you understand", None, 0, "skip", "Passed on crypto")]}

    def _ev_inheritance(self):
        self.inheritance_done = True
        g = self.wage(3000)
        opts = [self.O(f"Keep it as an emergency fund (+{money(g)} cash)", None, 0, "cash", f"Inherited {money(g)}", cash=g),
                self.O(f"Invest it (+{money(g)} investments)", None, 0, "info", f"Invested a {money(g)} inheritance", invest=g)]
        if self.card + self.loans > 0:
            opts.append(self.O("Pay down debt with it", None, 0, "good", "Paid debt with an inheritance", cash=g, pay_debt=g))
        return {"title": "Small Inheritance",
                "desc": f"A great-aunt you barely knew left you {money(g)}.", "options": opts}

    def _ev_accident(self):
        c = self.price(1800)
        return {"title": "Fender Bender",
                "desc": f"Someone backed into you. Your insurance deductible is {money(c)}.",
                "options": [
                    self.O(f"Pay {money(c)} cash", "cash", c, "cash", "Paid the deductible"),
                    self.O(f"Charge {money(c)} to card", "card", c, "card", "Charged the deductible"),
                    self.O(self._loan_label(c), "loan", c, "loan", "Deductible payment plan"),
                    self._collect_option(c, "Insurance deductible")]}

    def _ev_scam(self):
        c = self.price(500)
        return {"title": "Urgent Call from the 'IRS'",
                "desc": f"A caller says you owe back taxes and will be arrested unless you pay {money(c)} in gift cards today.",
                "options": [
                    self.O("Hang up and report the number", None, 0, "good", "Spotted a scam call", happiness=5,
                           popup={"title": "Scam avoided!", "kind": "success",
                                  "body": "<p>Real tax agencies never call demanding gift cards, wire transfers or crypto. "
                                          "Hang up, and contact the agency directly using its official number.</p>"}),
                    self.O(f"Pay {money(c)} in gift cards", "cash", c, "bad", f"Lost {money(c)} to a phone scam", happiness=-10,
                           popup={"title": "That was a scam", "kind": "warning",
                                  "body": "<p>The money is gone — gift cards are untraceable. Real tax agencies never demand "
                                          "gift cards or threaten arrest over the phone.</p>"})]}

    def _ev_dip(self):
        before = self.investments
        self.investments = int(self.investments * 0.88)
        self.add_log(f"Markets slid 12% — investments fell {money(before - self.investments)}", "bad")
        b = self.price(1000)
        fee = int(self.investments * self.withdraw_fee_rate())
        return {"title": "Market Slump",
                "desc": f"Markets fell 12% this quarter and your portfolio dropped to {money(self.investments)}. "
                        "Headlines are screaming 'recession'.",
                "info": "Historically, markets have recovered from every slump — but selling in a panic locks in your losses.",
                "options": [
                    self.O("Hold steady", None, 0, "skip", "Held investments through the slump"),
                    self.O(f"Buy the dip: invest {money(b)} cash", "cash", b, "cash", f"Bought the dip ({money(b)})", invest=b),
                    self.O(f"Panic-sell everything (fee {money(fee)})", None, 0, "bad", "Panic-sold investments", sell_all=True)]}

    def _ev_bonus(self):
        b = self.wage(1000)
        return {"title": "Year-End Bonus",
                "desc": f"Great work this year! Your manager hands you a {money(b)} bonus.",
                "options": [
                    self.O(f"Save it (+{money(b)} cash)", None, 0, "cash", f"Saved a {money(b)} bonus", cash=b),
                    self.O(f"Invest it (+{money(b)} investments)", None, 0, "info", f"Invested a {money(b)} bonus", invest=b),
                    self.O("Celebrate (+20 happiness)", None, 0, "card", "Celebrated the bonus", happiness=20)]}

    def _ev_holiday(self):
        c = self.price(550)
        return {"title": "Holiday Season",
                "desc": "Gifts, travel home and holiday dinners. Everyone else seems to be spending.",
                "options": [
                    self.O(f"Celebrate: {money(c)} cash  (+12 happiness)", "cash", c, "cash", "Holiday celebrations", happiness=12),
                    self.O(f"Celebrate: charge {money(c)} to card  (+12 happiness)", "card", c, "card", "Holidays on the card", happiness=12),
                    self.O("Skip gifts this year  (-15 happiness)", None, 0, "skip", "Skipped the holidays", happiness=-15)]}

    def _ev_debt_offer(self):
        owed = self.card + self.loans
        pay = min(owed, self.price(1000))
        waive = min(owed - pay, self.price(100))
        return {"title": "Pay-Down Challenge",
                "desc": f"Your bank will waive {money(waive)} of fees if you pay {money(pay)} toward your debt right now. "
                        "This counts toward your minimum payment.",
                "options": [
                    self.O(f"Pay {money(pay)} now" + (f" ({money(waive)} waived)" if waive else ""), None, 0, "good",
                           "Took the pay-down challenge", need=pay, pay_debt=pay, waive=waive),
                    self.O("Not now", None, 0, "skip", "Skipped the pay-down challenge")]}

    # ------------------------------------------------------ option choices --
    def option_block_reason(self, o):
        p, a = o["pay"], o["amount"]
        if p == "cash" and self.cash < a:
            return f"need {money(a)} cash"
        if p == "card" and self.card_available() < a:
            return f"only {money(self.card_available())} card credit left"
        if p == "loan":
            r = self.loan_block_reason(a)
            if r:
                return r[0].lower() + r[1:]
        if o["need"] and self.cash < o["need"]:
            return f"need {money(o['need'])} cash"
        return None

    def _apply_fx(self, fx):
        for k, v in fx.items():
            if k == "happiness":
                self.happiness = max(0, min(100, self.happiness + v))
            elif k == "cash":
                self.cash += v
            elif k == "invest":
                self.investments += v
                self.unlock("investor")
            elif k == "income":
                self.base_income += v
            elif k == "rent":
                self.rent_adj = max(-600, self.rent_adj + v)
            elif k == "roommate":
                self.has_roommate = True
            elif k == "has_car":
                self.has_car = v
            elif k == "pet":
                self.has_pet = True
            elif k == "layoff":
                self.layoff_turns, self.layoff_mult = v
                self.moment("Laid off", "bad")
            elif k == "course":
                self.courses_taken += 1
                self.base_income += self.COURSE_BONUS
                self.moment(f"Earned certification {self.courses_taken}/{self.MAX_COURSES}", "good")
                if self.courses_taken >= self.MAX_COURSES:
                    self.unlock("learner")
            elif k == "limit_bonus":
                self.limit_bonus += v
            elif k == "card_charge":
                self.card += v
                self._note_debt()
            elif k == "pay_debt":
                pay = min(v, self.card + self.loans, max(0, self.cash))
                if pay > 0:
                    self._apply_payment(pay)
                    self.add_log(f"Paid {money(pay)} toward debt", "good")
            elif k == "waive":
                w = min(v, self.loans)
                self.loans -= w
                self.card -= min(v - w, self.card)
            elif k == "sell_all":
                amt = self.investments
                fee = int(amt * self.withdraw_fee_rate())
                self.investments = 0
                self.cash += amt - fee
                self.stats["fees"] += fee
            elif k == "gamble":
                chance, win, lose = v
                won = self.rng.random() < chance
                res = dict(win if won else lose)
                log = res.pop("log", "")
                self._apply_fx(res)
                if log:
                    self.add_log(log, "good" if won else "warn")
            elif k == "popup":
                self.popups.append(v)

    def choose_option(self, idx):
        ev = self.current_event
        if self.state != "event" or ev is None:
            return False, ""
        o = ev["options"][idx]
        reason = self.option_block_reason(o)
        if reason:
            return False, reason
        start_score = self.credit_score
        self.credit_reasons = []
        p, a = o["pay"], o["amount"]
        if p == "cash":
            self.cash -= a
        elif p == "card":
            self.card += a
            self._note_debt()
            self.unlock("first_swipe")
        elif p == "loan":
            fee = math.ceil(a * self.LOAN_ORIGINATION)
            self.loans += a + fee
            self.stats["fees"] += fee
            self._note_debt()
        elif p == "collections":
            self._collections(a, o["log"] or "Bill")

        fx = dict(o["fx"])
        quiz = fx.pop("quiz", None)
        self._apply_fx(fx)

        if o["log"] and p != "collections":
            tone = {"cash": "info", "card": "card", "loan": "warn", "bad": "bad", "good": "good", "info": "invest"}.get(o["tone"], "info")
            self.add_log(o["log"] + (f" (-{money(a)})" if p == "cash" and a else
                                     f" ({money(a)} on card)" if p == "card" else
                                     f" ({money(a)} loan)" if p == "loan" else ""), tone)

        if quiz is not None:
            if quiz:
                prize = int(round(self.price(150), -1))
                self.cash += prize
                self.happiness = min(100, self.happiness + 5)
                self.quiz_correct += 1
                if self.quiz_correct >= 3:
                    self.unlock("quiz_whiz")
                self.add_log(f"Aced the credit quiz! +{money(prize)} gift card", "good")
                title, kind = "Correct!", "success"
            else:
                self.add_log("Missed the credit quiz question", "warn")
                title, kind = "Not quite", "info"
            correct = next(x["label"] for x in ev["options"] if x["fx"].get("quiz"))
            self.popups.append({"title": title, "kind": kind,
                                "body": f"<p><b>Answer:</b> {esc(correct)}</p><p>{esc(ev['explain'])}</p>"})

        self._milestones()
        self._credit_drop_popup(start_score)
        self.current_event = None
        self.state = "main"
        return True, ""
