// Copyright 2015 Esri 
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//    http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

using System;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using MilitaryPlanner.ViewModels;

namespace MilitaryPlanner.Tests
{
    [TestClass]
    public class MilitaryPlannerTests
    {
        #region Mission View Model tests
        [TestMethod]
        public void MissionVM()
        {
            var missionViewModel = new MissionViewModel();
            Assert.AreEqual(0, missionViewModel.PhaseCount);
            //Assert.AreEqual(0, missionViewModel.CurrentMission.MilitaryMessages.Count);
            Assert.AreEqual(0, missionViewModel.CurrentMission.PhaseList.Count);
            Assert.AreEqual(0, missionViewModel.CurrentPhaseIndex);
        }
        [TestMethod]
        public void AddPhase()
        {
            var missionViewModel = new MissionViewModel();
            missionViewModel.CurrentMission.AddPhase("temp");
            Assert.AreEqual(1, missionViewModel.PhaseCount);
        }

        [TestMethod]
        public void DeletePhaseCommand()
        {
            var missionViewModel = new MissionViewModel();
            missionViewModel.CurrentMission.AddPhase("temp");
            missionViewModel.CurrentMission.AddPhase("temp");
            missionViewModel.DeletePhaseCommand.Execute(true);
            Assert.AreEqual(1, missionViewModel.PhaseCount);
        }

        [TestMethod]
        public void NextPhaseCommand()
        {
            var missionViewModel = new MissionViewModel();
            missionViewModel.CurrentMission.AddPhase("temp");
            missionViewModel.CurrentMission.AddPhase("temp");
            missionViewModel.CurrentPhaseIndex = 0;
            missionViewModel.PhaseNextCommand.Execute(null);
            missionViewModel.PhaseNextCommand.Execute(null);
            Assert.AreEqual(1, missionViewModel.CurrentPhaseIndex);
        }

        [TestMethod]
        public void BackPhaseCommand()
        {
            var missionViewModel = new MissionViewModel();
            missionViewModel.CurrentMission.AddPhase("temp");
            missionViewModel.CurrentMission.AddPhase("temp");
            missionViewModel.PhaseBackCommand.Execute(null);
            missionViewModel.PhaseBackCommand.Execute(null);
            Assert.AreEqual(0, missionViewModel.CurrentPhaseIndex);
        }

        #endregion

        #region  Base Tool View Model test
        [TestMethod]
        public void BaseToolToggle()
        {
            var tool = new BaseToolViewModel();
            Assert.IsFalse(tool.IsToolOpen);
            tool.Toggle();
            Assert.IsTrue(tool.IsToolOpen);
        }

        [TestMethod]
        public void BaseToolOpenCommand()
        {
            var tool = new BaseToolViewModel();
            tool.OpenToolCommand.Execute(null);
            Assert.IsTrue(tool.IsToolOpen);
        }
        
        [TestMethod]
        public void BaseToolCloseCommand()
        {
            var tool = new BaseToolViewModel();
            tool.CloseToolCommand.Execute(null);
            Assert.IsFalse(tool.IsToolOpen);
        }
        #endregion

        #region OOB View Model
        
        [TestMethod]
        public void OOBSearch()
        {
            var oobvm = new OrderOfBattleViewModel();

            oobvm.SearchString = "light,infantry";
            oobvm.SearchCommand.Execute(null);
            Assert.IsTrue(oobvm.Symbols.Count > 0);
        }
        
        #endregion

    }
}
